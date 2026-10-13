"""Loopback-only saved-audio browser judge; never opens a microphone."""

import argparse
import http.client
import http.server
import json
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8772)
    parser.add_argument("--clips", type=Path, default=ROOT / "runs/voice-endpoint-001")
    parser.add_argument("--browser-port", type=int, default=8766)
    parser.add_argument("--native-port", type=int, default=8765)
    parser.add_argument("--trim-speech", action="store_true",
                        help="Experimental maintained-Silero edge preprocessing before ASR")
    parser.add_argument(
        "--physical-checks",
        action="store_true",
        help="Enable only listed simulator API routes for the physical Stop judge",
    )
    parser.add_argument("--local-asr", action="store_true",
                        help="Use this probe's warmed SpeechInput, avoiding the extra relay decode")
    parser.add_argument("--speech-checks", action="store_true",
                        help="Enable isolated browser-local speech output; never controls an arm")
    args = parser.parse_args()
    from physical_ai_lab.dume.speech import Speech
    speech = Speech() if args.speech_checks else None
    voice = None
    voice_lock = threading.Lock()
    if args.local_asr:
        from physical_ai_lab.dume.asr import SpeechInput

        voice = SpeechInput(edge_trim=args.trim_speech)
        voice._prepare()
        if voice.status != "ready":
            raise RuntimeError(voice.error)
        print(json.dumps({"speech_input": voice.snapshot()}), flush=True)
    routes = {
        "/": ROOT / "integrations/speech-vad/benchmark.html",
        "/physical": ROOT / "integrations/speech-vad/physical-stop.html",
        "/acknowledgment": ROOT / "integrations/speech-vad/acknowledgment.html",
        "/tts-diagnostic": ROOT / "integrations/speech-vad/tts-diagnostic.html",
        "/local-speech.mjs": ROOT / "src/physical_ai_lab/dume/web/local-speech.mjs",
        "/physical-speech.mjs": ROOT / "integrations/speech-vad/physical-speech.mjs",
        "/acknowledgment.wav": ROOT / ".cache/local-speech/acknowledgment.wav",
        "/voice-input.mjs": ROOT / "src/physical_ai_lab/dume/web/voice-input.mjs",
        "/speech-detector.mjs": ROOT / "src/physical_ai_lab/dume/web/speech-detector.mjs",
    }
    folders = {
        "/vad/": ROOT / ".cache/speech-vad",
        "/ort/": ROOT / ".cache/speech-vad",
        "/clips/": args.clips.resolve(),
        "/speech-vad/": ROOT / ".cache/speech-vad",
    }

    class Handler(http.server.SimpleHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, format, *values):
            # High-frequency state sampling must not fill the PTY and delay
            # serving requests. Preserve errors locally instead of flooding it.
            if format.startswith("code ") or (
                len(values) > 1 and str(values[1]) not in {"200", "304"}
            ):
                with (args.clips / "probe-errors.log").open("a") as file:
                    file.write(f"{time.time()} {format % values}\n")

        def forward(self, method, port, route, body=None, headers=None):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            try:
                connection.request(method, route, body, headers or {})
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.getheader(
                    "Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (OSError, http.client.HTTPException) as error:
                with (args.clips / "probe-errors.log").open("a") as file:
                    file.write(f"{time.time()} {method} {port}{route}: {error!r}\n")
                data = json.dumps({"detail": "Qualification proxy request failed."}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            finally:
                connection.close()

        def do_GET(self):
            route = urlsplit(self.path).path
            if args.physical_checks and route in {"/api/state", "/api/native-state"}:
                self.forward(
                    "GET", args.native_port if route == "/api/native-state"
                    else args.browser_port, "/state"
                )
                return
            if args.physical_checks and (route in {"/api/frame.jpg", "/acknowledgment.wav"}
                                         or route.startswith("/speech-audio/")):
                self.forward("GET", args.browser_port, route.removeprefix("/api"))
                return
            selected = routes.get(route)
            for prefix, folder in folders.items():
                if route.startswith(prefix):
                    candidate = (folder / route[len(prefix) :]).resolve()
                    if candidate.is_relative_to(folder.resolve()):
                        selected = candidate
            if selected is None or not selected.is_file():
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(str(selected)))
            self.send_header("Content-Length", str(selected.stat().st_size))
            self.end_headers()
            self.wfile.write(selected.read_bytes())

        def do_POST(self):
            if args.physical_checks and (self.path in {"/api/speak", "/api/speech-stop"}
                                        or self.path.startswith(("/api/speech-started/",
                                                                 "/api/speech-finished/"))):
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 10_000:
                    self.send_error(413)
                    return
                connection = http.client.HTTPConnection("127.0.0.1", args.browser_port, timeout=15)
                try:
                    connection.request("POST", self.path.removeprefix("/api"),
                                       self.rfile.read(size),
                                       {"Content-Type": "application/json"})
                    response = connection.getresponse()
                    result = json.loads(response.read())
                    data = json.dumps(result).encode()
                    self.send_response(response.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                finally:
                    connection.close()
                return
            if speech and self.path in {"/speak", "/speech-stop"}:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 2000:
                    self.send_error(413)
                    return
                body = json.loads(self.rfile.read(size))
                result = (
                    speech.speak(body["message"][:500]) if self.path == "/speak" else speech.stop()
                )
                if (result and body.get("message") == "Let me check."
                        and routes["/acknowledgment.wav"].is_file()):
                    result["audio"] = "/acknowledgment.wav"
                with (args.clips / "speech-events.jsonl").open("a") as file:
                    file.write(json.dumps({"time": time.time(), "route": self.path,
                                           "result": result}) + "\n")
                data = json.dumps(result or {}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if speech and self.path.startswith(("/speech-started/", "/speech-finished/")):
                size = int(self.headers.get("Content-Length", "0"))
                if size:
                    self.rfile.read(size)
                generation = int(self.path.rsplit("/", 1)[1])
                if self.path.startswith("/speech-started/"):
                    speech.started(generation)
                else:
                    speech.finished(generation)
                with (args.clips / "speech-events.jsonl").open("a") as file:
                    file.write(json.dumps({"time": time.time(), "route": self.path,
                                           "generation": generation}) + "\n")
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")
                return
            if args.physical_checks and self.path in {"/api/interact", "/api/stop", "/api/reset"}:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 10_000:
                    self.send_error(413)
                    return
                self.forward(
                    "POST",
                    args.browser_port,
                    self.path.removeprefix("/api"),
                    self.rfile.read(size),
                    {"Content-Type": "application/json"},
                )
                return
            if self.path == "/transcribe":
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2_000_000:
                    self.send_error(413)
                    return
                if voice is not None:
                    try:
                        with voice_lock:
                            decoded = voice._recognize(self.rfile.read(size))
                        status = 200
                    except ValueError as error:
                        decoded, status = {"detail": str(error)}, 422
                    data = json.dumps(decoded).encode()
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                connection = http.client.HTTPConnection("127.0.0.1", args.browser_port, timeout=30)
                try:
                    audio = self.rfile.read(size)
                    preprocessing = None
                    if args.trim_speech:
                        from speech_edge_preprocessing import prepare_speech

                        try:
                            audio, preprocessing = prepare_speech(audio)
                        except ValueError as error:
                            data = json.dumps({"detail": str(error)}).encode()
                            self.send_response(422)
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Content-Length", str(len(data)))
                            self.end_headers()
                            self.wfile.write(data)
                            return
                    connection.request(
                        "POST",
                        "/transcribe",
                        audio,
                        {
                            "Content-Type": "audio/wav" if args.trim_speech
                            else self.headers.get("Content-Type", "audio/webm"),
                            "X-Dume-Voice-Mode": self.headers.get("X-Dume-Voice-Mode", "request"),
                            "X-Dume-Capture-Metrics":
                                self.headers.get("X-Dume-Capture-Metrics", "{}"),
                        },
                    )
                    response = connection.getresponse()
                    data = response.read()
                    if preprocessing and response.status == 200:
                        decoded = json.loads(data)
                        decoded["speech_edge_preprocessing"] = preprocessing
                        data = json.dumps(decoded).encode()
                    self.send_response(response.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                finally:
                    connection.close()
                return
            if self.path != "/report":
                self.send_error(404)
                return
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size < 2_000_000:
                self.send_error(413)
                return
            data = json.loads(self.rfile.read(size))
            name = {
                "stream": "silero-stream.json",
                "asr-stream": "silero-asr-stream.json",
                "physical-stop": "physical-stop-browser.json",
                "acknowledgment": "acknowledgment-browser.json",
                "tts-diagnostic": "tts-diagnostic-browser.json",
            }.get(data.get("kind"), "silero-browser.json")
            (args.clips / name).write_text(json.dumps(data, indent=2) + "\n")
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

    class ProbeServer(http.server.ThreadingHTTPServer):
        request_queue_size = 128

    server = ProbeServer(("127.0.0.1", args.port), Handler)
    print(f"Saved-audio judge: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if voice:
            voice.close()


if __name__ == "__main__":
    main()
