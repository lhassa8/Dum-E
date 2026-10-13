"""Loopback-only saved-audio browser judge; never opens a microphone."""

import argparse
import http.client
import http.server
import json
import threading
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
    args = parser.parse_args()
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
        def forward(self, method, port, route, body=None, headers=None):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            try:
                connection.request(method, route, body, headers or {})
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json")
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
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(decoded).encode())
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
                            self.send_response(422)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"detail": str(error)}).encode())
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
                    self.end_headers()
                    self.wfile.write(data)
                finally:
                    connection.close()
                return
            if self.path != "/report":
                self.send_error(404)
                return
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size < 100_000:
                self.send_error(413)
                return
            data = json.loads(self.rfile.read(size))
            name = {
                "stream": "silero-stream.json",
                "asr-stream": "silero-asr-stream.json",
                "physical-stop": "physical-stop-browser.json",
            }.get(data.get("kind"), "silero-browser.json")
            (args.clips / name).write_text(json.dumps(data, indent=2) + "\n")
            self.send_response(200)
            self.end_headers()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Saved-audio judge: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if voice:
            voice.close()


if __name__ == "__main__":
    main()
