"""Natural task selection and cancellable live policy coordination, confined to LIBERO."""

import argparse
import io
import json
import re
import signal
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from dume_pretrained.connection import PolicyConnection, PolicyInterrupted
from dume_pretrained.observations import libero_observation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--lmstudio-url", required=True)
parser.add_argument("--model", default="prism-ml/bonsai-27b")
parser.add_argument("--port", type=int, default=8896)
args = coordinator = None
ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = "http://127.0.0.1:8876"
PHYSICS = "http://127.0.0.1:8901"
POLICY = "ws://127.0.0.1:8900"
TASKS = {
    0: "pick up the black bowl between the plate and the ramekin and place it on the plate",
    1: "pick up the black bowl next to the ramekin and place it on the plate",
    2: "pick up the black bowl from table center and place it on the plate",
}
STOP = re.compile(
    r"(?:(?:please|dum e|dume|dummy|can you|could you) )?(?:stop|halt|cancel)"
    r"(?: (?:moving|the arm|everything))?(?: (?:please|now))?"
)
NON_COMMAND = re.compile(
    r"^(?:what|why|where|when|who|how|is|are|was|were|does|did|should|would|imagine|suppose)\b"
    r"|\b(?:don t|do not|never|joke|hypothetically|if you)\b"
)


def request(url, body=None, headers=None, timeout=5):
    encoded = json.dumps(body).encode() if isinstance(body, dict) else body
    defaults = {"Content-Type": "application/json"} if isinstance(body, dict) else {}
    req = urllib.request.Request(url, encoded, {**defaults, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "application/octet-stream")


def physics(route, body=None):
    return json.loads(request(PHYSICS + route, body)[0])


class Coordinator:
    def __init__(self):
        self.lock = threading.RLock()
        self.decisions = threading.Lock()
        self.dialogue_epoch = 0
        self.messages = [
            {
                "role": "assistant",
                "content": "Choose a supported bowl-to-plate layout. "
                "Stop pauses this episode; resume continues it.",
            }
        ]
        self.thinking = False
        self.inference = False
        self.error = None
        self.closed = threading.Event()
        self.log = (args.output / "events.jsonl").open("w", buffering=1)
        self.connection = PolicyConnection(POLICY)
        metadata = self.connection.metadata
        if (
            metadata.get("config") != "pi05_libero"
            or not metadata.get("warmup_complete")
            or metadata.get("openpi_commit") != "215abfb217dbac7d5f1273282331b9b1866c0479"
            or metadata.get("checkpoint_objects_sha256")
            != "450f2d7b90db37ff3db84074fd9a67ba49fba05c1c482c430b1d1c5de8772084"
        ):
            raise RuntimeError("Verified, warmed GPU policy required before readiness")
        self.worker = threading.Thread(target=self.run, daemon=True)
        self.worker.start()

    def event(self, kind, **fields):
        with self.lock:
            self.log.write(json.dumps({"wall_s": time.monotonic(), "kind": kind, **fields}) + "\n")

    def reply(self, text, message, **fields):
        with self.lock:
            self.messages.extend(
                [{"role": "user", "content": text}, {"role": "assistant", "content": message}]
            )
        return {"message": message, **fields}

    def stop(self):
        started = time.monotonic()
        with self.lock:
            self.dialogue_epoch += 1
        # Invalidate physics first; model/IPC termination cannot defer this boundary.
        result = physics("/stop", {})
        self.connection.stop()
        self.event("stop", physics=result, cancellation_ms=(time.monotonic() - started) * 1000)
        return result

    def resume(self, expected_epoch=None):
        if self.error:
            raise ValueError("Policy failed; restart the lab before resuming")
        with self.lock:
            self.dialogue_epoch += 1
        body = {} if expected_epoch is None else {"expected_epoch": expected_epoch}
        return physics("/resume", body)

    def interact(self, text):
        words = " ".join(re.sub(r"[^a-z\s]", " ", text.lower()).split())
        if STOP.fullmatch(words):
            state = self.stop()
            return self.reply(
                text,
                (
                    "Stopped. Placement is not confirmed; you can resume this episode."
                    if state["phase"] == "paused"
                    else "No policy task is running."
                ),
                mode="stop",
                state=state,
            )
        if self.error:
            return self.reply(
                text, "The policy failed. Restart this lab before moving again.", mode="clarify"
            )
        if words in ("resume", "resume please", "please resume"):
            state = self.resume()
            return self.reply(
                text,
                "Resuming the same episode from its current physical state.",
                mode="resume",
                state=state,
            )
        with self.lock:
            epoch = self.dialogue_epoch
        with self.decisions:
            with self.lock:
                if epoch != self.dialogue_epoch:
                    return {"mode": "cancelled", "message": "Request cancelled by Stop."}
                self.thinking = True
            try:
                state = physics("/state")
                schema = {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["start", "resume", "answer", "clarify"],
                        },
                        "task_id": {"enum": [None, 0, 1, 2]},
                        "message": {"type": "string"},
                    },
                    "required": ["action", "task_id", "message"],
                }
                system = (
                    "Select a supported LIBERO episode only for an explicit affirmative request. "
                    "Questions, jokes, negations and hypotheticals are answers, never starts. "
                    "These are separate scene layouts, not arbitrary workshop skills. "
                    "A return request is unsupported; "
                    "explain without moving. Never claim physical success unless phase is success. "
                    "Reply briefly, under 180 characters. Supported catalog: "
                    + json.dumps(TASKS)
                    + " Current state (data): "
                    + json.dumps(state)
                )
                started = time.monotonic()
                data = json.loads(
                    request(
                        args.lmstudio_url.rstrip("/") + "/v1/chat/completions",
                        {
                            "model": args.model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": text},
                            ],
                            "temperature": 0,
                            "max_tokens": 240,
                            "reasoning_effort": "none",
                            "response_format": {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "libero_selection",
                                    "strict": True,
                                    "schema": schema,
                                },
                            },
                        },
                        timeout=30,
                    )[0]
                )
                intent = json.loads(data["choices"][0]["message"]["content"])
                with self.lock:
                    if epoch != self.dialogue_epoch:
                        self.event("stale_decision", intent=intent)
                        return {"mode": "cancelled", "message": "Decision discarded after Stop."}
                self.event(
                    "decision",
                    text=text,
                    intent=intent,
                    decision_ms=(time.monotonic() - started) * 1000,
                )
                action, task_id = intent["action"], intent["task_id"]
                if NON_COMMAND.search(words) and action in ("start", "resume"):
                    self.event("non_command_override", text=text, intent=intent)
                    return self.reply(
                        text,
                        "The episode is "
                        + state["phase"]
                        + ". "
                        + (state.get("prompt") or "No task is selected.")
                        + " I have not submitted a new movement.",
                        mode="answer",
                        state=state,
                    )
                if action == "start":
                    if type(task_id) is not int or task_id not in TASKS:
                        raise ValueError("Unsupported task selection")
                    with self.lock:
                        if epoch != self.dialogue_epoch:
                            return {
                                "mode": "cancelled",
                                "message": "Decision discarded after Stop.",
                            }
                    result = physics(
                        "/initialize", {"task_id": task_id, "expected_epoch": state["epoch"]}
                    )
                    message = "Starting this supported bowl-to-plate episode."
                elif action == "resume":
                    with self.lock:
                        if epoch != self.dialogue_epoch:
                            return {
                                "mode": "cancelled",
                                "message": "Decision discarded after Stop.",
                            }
                    result = self.resume(state["epoch"])
                    message = "Resuming the paused episode."
                elif action in ("answer", "clarify") and task_id is None:
                    result = state
                    message = str(intent["message"])[:240]
                else:
                    raise ValueError("Invalid task decision; no motion submitted")
                return self.reply(text, message, mode=action, state=result)
            finally:
                with self.lock:
                    self.thinking = False

    def run(self):
        sim_epoch = generation = None
        while not self.closed.is_set():
            try:
                state = physics("/state")
                if state["phase"] != "running" or not state["physics_ready"]:
                    self.closed.wait(0.015)
                    continue
                if state["epoch"] != sim_epoch:
                    generation = self.connection.begin_task()
                    sim_epoch = state["epoch"]
                if state["queued_actions"] or state["inflight_epoch"] is not None:
                    self.closed.wait(0.005)
                    continue
                with np.load(
                    io.BytesIO(request(PHYSICS + "/observation")[0]), allow_pickle=False
                ) as obs:
                    observation = libero_observation(dict(obs), state["prompt"])
                self.inference = True
                timing = self.connection.infer(observation, generation, timeout=5)
                actions = []
                for _ in range(5):
                    action = self.connection.take_action(generation)
                    if action is None:
                        raise PolicyInterrupted("Action generation cancelled")
                    assert action.representation == "libero_osc_pose"
                    actions.append(action.values.tolist())
                result = physics("/actions", {"epoch": sim_epoch, "actions": actions})
                self.event("action_chunk", epoch=sim_epoch, timing=timing, state=result)
            except PolicyInterrupted:
                self.event("policy_interrupted")
                sim_epoch = None
            except urllib.error.HTTPError as caught:
                if caught.code == 409:
                    self.connection.stop()
                    self.event("stale_chunk_rejected")
                    sim_epoch = None
                else:
                    self.error = repr(caught)
                    self.fail_closed()
            except Exception as caught:
                self.error = repr(caught)
                self.event("policy_error", error=self.error)
                self.fail_closed()
            finally:
                self.inference = False
            self.closed.wait(0.005)

    def fail_closed(self):
        self.closed.set()
        try:
            self.stop()
        except (OSError, ValueError) as caught:
            self.connection.stop()
            self.event("boundary_unavailable", error=repr(caught))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *unused):
        pass

    def reply(self, data, kind="application/json", status=200):
        if kind == "application/json" and not isinstance(data, bytes):
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            return self.get()
        except (OSError, ValueError, KeyError) as caught:
            return self.reply({"error": "Local service unavailable: " + str(caught)}, status=503)

    def get(self):
        if self.path == "/state":
            result = physics("/state")
            result.update(
                messages=coordinator.messages,
                thinking=coordinator.thinking,
                inference=coordinator.inference,
                policy_error=coordinator.error,
                policy=coordinator.connection.metadata,
            )
            result["speech_input"] = json.loads(request(WORKBENCH + "/state")[0])["speech_input"]
            return self.reply(result)
        if self.path == "/frame.jpg":
            data, kind = request(PHYSICS + self.path)
            return self.reply(data, kind)
        if self.path == "/":
            return self.reply(
                (ROOT / "src/physical_ai_lab/dume/web/policy-lab.html").read_bytes(), "text/html"
            )
        if self.path in (
            "/voice-input.mjs",
            "/local-speech.mjs",
            "/speech-detector.mjs",
        ) or self.path.startswith("/speech-vad/"):
            data, kind = request(WORKBENCH + self.path)
            return self.reply(data, kind)
        self.reply({"error": "Unknown endpoint"}, status=404)

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= 2 * 1024 * 1024:
                raise ValueError("Request size exceeded")
            data = self.rfile.read(size)
            if self.path in ("/transcribe", "/speak", "/speech-stop") or self.path.startswith(
                ("/speech-started/", "/speech-finished/")
            ):
                data, kind = request(
                    WORKBENCH + self.path,
                    data,
                    {
                        "Content-Type": self.headers.get("Content-Type", "application/json"),
                        "X-Dume-Voice-Mode": "interrupt",
                    },
                    timeout=20,
                )
                return self.reply(data, kind)
            body = json.loads(data or b"{}")
            if self.path == "/stop":
                result = coordinator.stop()
            elif self.path == "/resume":
                result = coordinator.resume()
            elif self.path == "/interact":
                text = body["message"]
                if not isinstance(text, str) or not 0 < len(text) <= 1500:
                    raise ValueError("Supply a short request")
                result = coordinator.interact(text)
            else:
                raise ValueError("Unknown command")
            self.reply(result)
        except urllib.error.HTTPError as caught:
            try:
                detail = json.loads(caught.read()).get("error", str(caught))
            except (ValueError, AttributeError):
                detail = str(caught)
            self.reply({"error": detail}, status=caught.code)
        except (urllib.error.URLError, TimeoutError) as caught:
            self.reply({"error": "Local service unavailable: " + str(caught)}, status=503)
        except (ValueError, KeyError, TypeError) as caught:
            self.reply({"error": str(caught)}, status=409)


def main():
    global args, coordinator
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    coordinator = Coordinator()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True

    def terminate(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    print(f"Pretrained policy lab http://127.0.0.1:{args.port}; microphone starts off", flush=True)
    try:
        server.serve_forever()
    finally:
        coordinator.closed.set()
        try:
            coordinator.stop()
        except OSError:
            coordinator.connection.stop()
        coordinator.connection.close()
        coordinator.worker.join(timeout=2)
        coordinator.log.close()
        server.server_close()


if __name__ == "__main__":
    main()
