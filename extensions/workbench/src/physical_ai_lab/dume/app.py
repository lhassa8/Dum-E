"""Launch the original Dum-E task/MCP stack with a local physics agent."""

import argparse
import asyncio
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from multiprocessing.managers import SharedMemoryManager
from pathlib import Path
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response

from physical_ai_lab.assistant.app import ChatRequest
from physical_ai_lab.dume.asr import MAX_AUDIO_BYTES, SpeechInput
from physical_ai_lab.dume.bridge import SimulationAgent, SimulationController
from physical_ai_lab.dume.speech import Speech
from physical_ai_lab.dume.upstream import VENDOR

# Upstream uses absolute 'shared' imports; load its isolated source path first.
# isort: split
from shared.fleet_manager import SharedMemoryFleetManager  # noqa: E402
from shared.message_broker import SharedMemoryMessageBroker  # noqa: E402
from shared.task_manager import SharedMemoryTaskManager  # noqa: E402

WEB = Path(__file__).parent / "web"
SPEECH_VAD = Path(__file__).resolve().parents[3] / ".cache/speech-vad"
SPEECH_VAD_FILES = {
    "bundle.min.js",
    "vad.worklet.bundle.min.js",
    "silero_vad_v5.onnx",
    "ort.wasm.min.js",
    "ort-wasm-simd-threaded.mjs",
    "ort-wasm-simd-threaded.wasm",
}


class InteractionRequest(ChatRequest):
    source: Literal["typed", "voice"] = "typed"


async def prepare_voice_after_language(speech_input, controller):
    """Warm speech after the large model's allocation/prefill, before mic ready.

    Startup ordering only: later Stop recognition is independent of language calls.
    """
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            state = await controller.state()
            if state.get("model_status") in {"ready", "unavailable"}:
                break
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.1)
    else:
        speech_input.status = "unavailable"
        speech_input.error = "Voice input unavailable: simulator startup timed out."
        return
    await speech_input.prepare()


def make_api(agent, mcp_process, tools=False, speech_input=None):
    speech = Speech()
    speech_input = speech_input or SpeechInput()

    @asynccontextmanager
    async def lifespan(api):
        worker = asyncio.create_task(agent.worker())
        voice_loader = (
            asyncio.create_task(prepare_voice_after_language(speech_input, agent.controller))
            if tools
            else None
        )
        # Start the original broker subscription before accepting any requests.
        await asyncio.sleep(0.1)
        try:
            yield
        finally:
            speech.stop()
            if voice_loader:
                voice_loader.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await voice_loader
            speech_input.close()
            if agent.active_id:
                with contextlib.suppress(Exception):
                    await agent.cancel()
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker
            await agent.controller.client.aclose()

    api = FastAPI(lifespan=lifespan)

    @api.middleware("http")
    async def local_only(request: Request, call_next):
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if origin and origin != f"http://{host}":
            return Response("Local requests only", status_code=403)
        return await call_next(request)

    @api.get("/")
    async def index():
        return FileResponse(WEB / ("index.html" if tools else "blocks.html"))

    @api.get("/voice-input.mjs")
    async def microphone_script():
        return FileResponse(WEB / "voice-input.mjs", media_type="application/javascript")

    @api.get("/local-speech.mjs")
    async def local_speech_script():
        return FileResponse(WEB / "local-speech.mjs", media_type="application/javascript")

    @api.get("/speech-detector.mjs")
    async def speech_detector_script():
        return FileResponse(WEB / "speech-detector.mjs", media_type="application/javascript")

    @api.get("/speech-vad/{filename}")
    async def speech_detector_asset(filename: str):
        if filename not in SPEECH_VAD_FILES:
            raise HTTPException(404, "Unknown speech detector asset")
        asset = SPEECH_VAD / filename
        if not asset.is_file():
            raise HTTPException(
                503, "Run scripts/prepare_speech_vad.py to prepare local voice input"
            )
        media_type = "application/javascript" if asset.suffix in {".js", ".mjs"} else None
        return FileResponse(asset, media_type=media_type)

    @api.get("/state")
    async def state():
        tasks = await agent.task_records()
        busy = any(t["status"] in {"pending", "running"} for t in tasks)
        try:
            snapshot = await agent.controller.state()
        except httpx.HTTPError as error:
            snapshot = {
                "phase": "Simulator unavailable",
                "model_status": "unavailable",
                "model_error": str(error),
                "objects": {},
                "targets": {},
            }
        snapshot.update(
            messages=agent.messages,
            tasks=tasks,
            busy=busy or snapshot.get("busy", False),
            active_task=agent.active_id,
            last_result=agent.last_result,
            upstream_revision="f09a96827ea60e4b18a55fa67e2acb97800dc46b",
            mcp_status="running" if mcp_process.poll() is None else "failed",
            speech=speech.snapshot(),
            speech_input=speech_input.snapshot(),
            interaction=agent.interaction.snapshot()
            if hasattr(agent, "interaction")
            else {"busy": False},
        )
        return snapshot

    @api.get("/frame.jpg")
    async def frame():
        try:
            image = await agent.controller.request("GET", "/frame.jpg")
        except httpx.HTTPError as error:
            raise HTTPException(503, "Simulator image unavailable") from error
        return Response(
            image.content, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
        )

    @api.get("/camera.jpg")
    async def camera_frame(frame: str | None = None):
        try:
            response = await agent.controller.request(
                "GET", "/camera.jpg", params={"frame": frame} if frame else None
            )
        except httpx.HTTPError as error:
            raise HTTPException(404, "Ask a camera question first.") from error
        return Response(
            response.content, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
        )

    @api.post("/chat")
    async def chat(request: ChatRequest):
        if mcp_process.poll() is not None:
            raise HTTPException(503, "Dum-E MCP server is offline; restart dume-sim.")
        snapshot = await state()
        if snapshot["busy"] or snapshot["model_status"] != "ready":
            raise HTTPException(409, "Wait until the simulator is ready, or press Stop.")
        # submit uses the same original broker/task manager as the MCP server.
        return {"accepted": True, "task_id": await agent.submit(request.message)}

    @api.post("/stop")
    async def stop():
        speech.stop()
        try:
            await agent.cancel()
        except httpx.HTTPError as error:
            raise HTTPException(503, "Could not contact the simulator to stop it.") from error
        return {"stopping": True}

    @api.post("/interact")
    async def interact(request: InteractionRequest):
        if not tools:
            raise HTTPException(409, "Interaction during work requires the tool scene.")
        from physical_ai_lab.assistant.tool_routing import is_stop_request

        if is_stop_request(request.message):
            speech.stop()
            return await agent.interaction.interact(request.message)
        if mcp_process.poll() is not None:
            raise HTTPException(503, "Dum-E MCP server is offline; restart dume-sim.")
        snapshot = await state()
        if snapshot["model_status"] != "ready":
            raise HTTPException(409, "The local language model is still loading.")
        try:
            return await agent.interaction.interact(request.message)
        except (httpx.HTTPError, RuntimeError, ValueError) as error:
            raise HTTPException(409, str(error)) from error

    @api.post("/transcribe")
    async def transcribe(request: Request):
        snapshot = await state()
        voice_mode = request.headers.get("x-dume-voice-mode", "request")
        if voice_mode not in {"request", "interrupt"}:
            raise HTTPException(400, "Unknown voice mode.")
        if (snapshot["busy"] and voice_mode != "interrupt") or (
            snapshot["model_status"] != "ready" and voice_mode != "interrupt"
        ):
            raise HTTPException(409, "Wait until Dum-E is ready before recording.")
        if not request.headers.get("content-type", "").startswith("audio/"):
            raise HTTPException(415, "Send an audio recording.")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_AUDIO_BYTES:
                raise HTTPException(413, "Recording is too large. Keep it under 15 seconds.")
            chunks.append(chunk)
        try:
            result = await speech_input.transcribe(b"".join(chunks))
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except RuntimeError as error:
            raise HTTPException(409, str(error)) from error
        except Exception as error:
            raise HTTPException(503, "Local transcription failed. Please try again.") from error
        # Only recognized text/metrics are logged. Audio bytes are never saved.
        result["voice_mode"] = voice_mode
        result["likely_echo"] = speech.is_echo(result["text"])
        with (agent.log_path.parent / "transcripts.jsonl").open("a") as file:
            file.write(json.dumps(result) + "\n")
        # Transcription alone cannot move the arm. The browser submits through /chat.
        return result

    @api.post("/speak")
    async def speak(request: ChatRequest):
        try:
            result = speech.speak(request.message[:500])
            with (agent.log_path.parent / "speech.jsonl").open("a") as file:
                file.write(json.dumps({"text": request.message[:500], **result}) + "\n")
            return result
        except OSError as error:
            raise HTTPException(503, "Local speech output is unavailable.") from error

    @api.post("/speech-finished/{generation}")
    async def speech_finished(generation: int):
        speech.finished(generation)
        return {"finished": True}

    @api.post("/speech-started/{generation}")
    async def speech_started(generation: int):
        speech.started(generation)
        return {"started": True}

    @api.post("/speech-stop")
    async def speech_stop():
        speech.stop()
        return {"stopped": True}

    @api.post("/reset")
    async def reset():
        snapshot = await state()
        if snapshot["busy"]:
            raise HTTPException(409, "Stop before resetting.")
        if hasattr(agent, "interaction"):
            agent.interaction.invalidate()
            agent.interaction.clarification = None
        await agent.controller.request("POST", "/reset")
        return {"resetting": True}

    return api


def check_port(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


def ensure_simulator(
    port,
    logdir,
    tools=False,
    vision_model=None,
    vision_coordinates="normalized_xy",
    camera_tools=False,
):
    url = f"http://127.0.0.1:{port}"
    try:
        response = httpx.get(url + "/state", timeout=2, trust_env=False)
    except httpx.ConnectError:
        response = None
    if response is not None:
        response.raise_for_status()
        state = response.json()
        if state.get("backend") != "workbench" or "last_outcome" not in state:
            raise RuntimeError(
                f"Port {port} is not a compatible Workbench. Stop it or choose a port."
            )
        if state["busy"]:
            raise RuntimeError(
                "Workbench is busy. Finish or stop that task before launching Dum-E."
            )
        expected = "tools" if tools else "blocks"
        if state.get("tool_control", "baseline") != ("camera" if camera_tools else "baseline"):
            raise RuntimeError(
                "The existing simulator uses a different tool controller. "
                "Choose an unused --sim-port."
            )
        if state.get("profile", "blocks") != expected:
            raise RuntimeError(
                f"The existing simulator uses {state.get('profile', 'blocks')} mode. "
                "Stop it before switching scenes, or select --blocks to keep the block demo."
            )
        requested_backend = os.environ.get("WORKBENCH_LANGUAGE_BACKEND", "mlx") if tools else "mlx"
        if state.get("language_backend", "mlx") != requested_backend:
            raise RuntimeError(
                "The existing native simulator uses a different language backend. "
                "Choose an unused --sim-port to start the requested backend."
            )
        if requested_backend == "mlx" and os.environ.get("WORKBENCH_MODEL"):
            requested_folder = Path(os.environ["WORKBENCH_MODEL"]).expanduser().resolve()
            loaded_model = state.get("language_model")
            if not loaded_model or Path(loaded_model).expanduser().resolve() != requested_folder:
                raise RuntimeError(
                    "The existing native simulator uses a different MLX model. "
                    "Choose an unused --sim-port to start the requested model."
                )
        if requested_backend == "lmstudio":
            from physical_ai_lab.assistant.lmstudio import normalize_server_url

            requested_model = os.environ.get("WORKBENCH_LMSTUDIO_MODEL")
            if not requested_model:
                raise RuntimeError("Choose an LM Studio model with --model before launching")
            if state.get("language_model") != requested_model:
                raise RuntimeError(
                    "The existing native simulator uses a different LM Studio model. "
                    "Choose an unused --sim-port to start the requested model."
                )
            requested_url = normalize_server_url(
                os.environ.get("WORKBENCH_LMSTUDIO_URL", "http://127.0.0.1:1234")
            )
            if state.get("language_endpoint") != requested_url:
                raise RuntimeError(
                    "The existing native simulator uses a different or unverified LM Studio "
                    "server. Choose an unused --sim-port to start the requested server."
                )
        if requested_backend == "codex" and state.get("language_model") != "gpt-6-luna":
            raise RuntimeError("The existing native simulator is not running GPT-6 Luna.")
        if tools:
            from physical_ai_lab.assistant.tool_scene import TOOL_PHYSICS_PROFILE

            if state.get("physics_profile") != TOOL_PHYSICS_PROFILE:
                raise RuntimeError(
                    "The existing native simulator uses older or unverified tool contacts. "
                    "Restart it, or choose an unused --sim-port to apply the current physics."
                )
        if vision_model:
            camera = state.get("camera", {})
            from physical_ai_lab.assistant.lmstudio import normalize_server_url

            expected_url = normalize_server_url(
                os.environ.get("WORKBENCH_LMSTUDIO_URL", "http://127.0.0.1:1234")
            )
            if (
                camera.get("model") != vision_model
                or camera.get("coordinates") != vision_coordinates
                or camera.get("endpoint") != expected_url
            ):
                raise RuntimeError(
                    "The existing simulator has a different or unverified camera model. "
                    "Choose an unused --sim-port for the requested camera."
                )
        print("Connected to existing local Workbench; it will remain running on exit.", flush=True)
        return None
    check_port(port)
    logfile = (logdir / "simulator.log").open("w")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "physical_ai_lab.assistant.app",
            "--port",
            str(port),
            "--log-dir",
            str(logdir / "physics"),
        ]
        + (["--tools"] if tools else [])
        + (["--camera-tools"] if camera_tools else [])
        + (
            ["--vision-model", vision_model, "--vision-coordinates", vision_coordinates]
            if vision_model
            else []
        ),
        stdout=logfile,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    logfile.close()
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Simulator exited. See {logdir / 'simulator.log'}")
            try:
                httpx.get(url + "/state", timeout=1, trust_env=False).raise_for_status()
                return process
            except httpx.HTTPError:
                time.sleep(0.2)
        raise TimeoutError("Simulator did not start in 30 seconds.")
    except BaseException:
        process.terminate()
        process.wait(timeout=10)
        raise


def _ignore_interrupt():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--sim-port", type=int, default=8765)
    parser.add_argument("--mcp-port", type=int, default=8001)
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--blocks", action="store_true", help="Run the earlier colored-block demo")
    parser.add_argument(
        "--camera-tools", action="store_true", help="Opt-in camera-based tool motion"
    )
    parser.add_argument("--language-backend", choices=["mlx", "lmstudio", "codex"])
    parser.add_argument("--model", help="MLX model folder or LM Studio model ID")
    parser.add_argument("--lmstudio-url", help="LM Studio server, default http://127.0.0.1:1234")
    parser.add_argument("--vision-model", help="Optional already loaded LM Studio vision instance")
    parser.add_argument(
        "--vision-coordinates", choices=["normalized_xy", "grid1000_yx"], default="normalized_xy"
    )
    args = parser.parse_args()
    from physical_ai_lab.assistant.tool_language import configure_tool_language

    try:
        if args.camera_tools and args.blocks:
            raise ValueError("Camera tool motion requires the tool scene")
        if args.vision_model and args.blocks:
            raise ValueError("Camera questions require the tool scene")
        if args.blocks and args.language_backend not in {None, "mlx"}:
            raise ValueError("External language backends currently require the tool scene")
        configure_tool_language(
            "mlx" if args.blocks else args.language_backend, args.model, args.lmstudio_url
        )
    except ValueError as error:
        parser.error(str(error))
    if len({args.port, args.sim_port, args.mcp_port}) != 3:
        parser.error("Browser, simulator and MCP ports must be different.")
    for port in [args.port, args.mcp_port]:
        try:
            check_port(port)
        except OSError:
            parser.error(f"Port {port} is in use; open the running app or choose another port.")
    logdir = (args.log_dir or Path("runs") / ("dume-" + uuid.uuid4().hex[:8])).resolve()
    logdir.mkdir(parents=True, exist_ok=False)
    sim = ensure_simulator(
        args.sim_port,
        logdir,
        tools=not args.blocks,
        vision_model=args.vision_model,
        vision_coordinates=args.vision_coordinates,
        camera_tools=args.camera_tools,
    )
    mcp = None
    try:
        manager = SharedMemoryManager()
        manager.start(initializer=_ignore_interrupt)
        with manager:
            namespace = "sim_" + uuid.uuid4().hex[:10]
            buffers = {
                "DUME_TASKS_BUF": manager.ShareableList([" " * 8192] * 64),
                "DUME_BROKER_BUF": manager.ShareableList([" " * 8192] * 128),
                "DUME_BROKER_META": manager.ShareableList([0]),
                "DUME_FLEET_BUF": manager.ShareableList([" " * 4096] * 8),
            }
            tasks = SharedMemoryTaskManager(namespace, buffers["DUME_TASKS_BUF"].shm.name)
            broker = SharedMemoryMessageBroker(
                namespace, buffers["DUME_BROKER_BUF"].shm.name, buffers["DUME_BROKER_META"].shm.name
            )
            fleet = SharedMemoryFleetManager(namespace, buffers["DUME_FLEET_BUF"].shm.name)
            controller = SimulationController(f"http://127.0.0.1:{args.sim_port}")
            controller.connect()
            asyncio.run(
                fleet.register_robot(
                    controller.id,
                    "Dum-E simulated Panda",
                    {"simulation": True, "controller": "mujoco", "hardware": False},
                )
            )
            env = {
                **os.environ,
                **{k: v.shm.name for k, v in buffers.items()},
                "DUME_NAMESPACE": namespace,
                "DUME_MCP_HOST": "127.0.0.1",
                "DUME_MCP_PORT": str(args.mcp_port),
                "FASTMCP_CHECK_FOR_UPDATES": "off",
            }
            with (logdir / "mcp.log").open("w") as file:
                mcp = subprocess.Popen(
                    [sys.executable, str(VENDOR / "mcp_server.py")],
                    env=env,
                    cwd=VENDOR,
                    stdout=file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            agent = SimulationAgent(
                controller, tasks, broker, logdir / "events.jsonl", tools=not args.blocks
            )
            (logdir / "launch.json").write_text(
                json.dumps(
                    {
                        "upstream_revision": "f09a96827ea60e4b18a55fa67e2acb97800dc46b",
                        "namespace": namespace,
                        "simulation": True,
                        "profile": "blocks" if args.blocks else "tools",
                        "robot": controller.id,
                        "browser_port": args.port,
                        "mcp_port": args.mcp_port,
                        "sim_port": args.sim_port,
                    },
                    indent=2,
                )
                + "\n"
            )
            print(
                f"Dum-E simulation: http://127.0.0.1:{args.port}\n"
                f"Original Dum-E MCP: http://127.0.0.1:{args.mcp_port}/mcp\n"
                f"Session evidence: {logdir}",
                flush=True,
            )
            try:
                uvicorn.run(
                    make_api(agent, mcp, tools=not args.blocks),
                    host="127.0.0.1",
                    port=args.port,
                    log_level="warning",
                )
            finally:
                if mcp.poll() is None:
                    mcp.terminate()
                    mcp.wait(timeout=10)
                for backend in [tasks.tasks, broker.buffer, broker.meta, fleet.registry]:
                    backend.shm.close()
    finally:
        if sim and sim.poll() is None:
            sim.terminate()
            sim.wait(timeout=10)


def terminate_launcher(signum, frame):
    # Uvicorn re-raises SIGTERM after shutdown. Translate it to Python unwinding
    # so owned native/MCP children are cleaned up by _main's finally blocks.
    raise KeyboardInterrupt


def main():
    previous = signal.signal(signal.SIGTERM, terminate_launcher)
    try:
        _main()
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    main()
