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


def make_api(agent, mcp_process, tools=False, speech_input=None):
    speech = Speech()
    speech_input = speech_input or SpeechInput()

    @asynccontextmanager
    async def lifespan(api):
        worker = asyncio.create_task(agent.worker())
        voice_loader = asyncio.create_task(speech_input.prepare()) if tools else None
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
            speech={
                "last_text": speech.last_text,
                "speaking": bool(speech.process and speech.process.poll() is None),
            },
            speech_input=speech_input.snapshot(),
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

    @api.post("/transcribe")
    async def transcribe(request: Request):
        snapshot = await state()
        if snapshot["busy"] or snapshot["model_status"] != "ready":
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
            raise HTTPException(503, "Local Mac speech output is unavailable.") from error

    @api.post("/speech-stop")
    async def speech_stop():
        speech.stop()
        return {"stopped": True}

    @api.post("/reset")
    async def reset():
        snapshot = await state()
        if snapshot["busy"]:
            raise HTTPException(409, "Stop before resetting.")
        await agent.controller.request("POST", "/reset")
        return {"resetting": True}

    return api


def check_port(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


def ensure_simulator(port, logdir, tools=False):
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
        if state.get("profile", "blocks") != expected:
            raise RuntimeError(
                f"The existing simulator uses {state.get('profile', 'blocks')} mode. "
                "Stop it before switching scenes, or select --blocks to keep the block demo."
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
        + (["--tools"] if tools else []),
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
    args = parser.parse_args()
    if len({args.port, args.sim_port, args.mcp_port}) != 3:
        parser.error("Browser, simulator and MCP ports must be different.")
    for port in [args.port, args.mcp_port]:
        try:
            check_port(port)
        except OSError:
            parser.error(f"Port {port} is in use; open the running app or choose another port.")
    logdir = (args.log_dir or Path("runs") / ("dume-" + uuid.uuid4().hex[:8])).resolve()
    logdir.mkdir(parents=True, exist_ok=False)
    sim = ensure_simulator(args.sim_port, logdir, tools=not args.blocks)
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


def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
