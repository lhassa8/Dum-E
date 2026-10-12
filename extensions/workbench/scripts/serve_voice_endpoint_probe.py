"""Loopback-only saved-audio browser judge; never opens a microphone."""

import argparse
import http.client
import http.server
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8772)
    parser.add_argument("--clips", type=Path, default=ROOT / "runs/voice-endpoint-001")
    parser.add_argument(
        "--physical-checks",
        action="store_true",
        help="Enable only listed simulator API routes for the physical Stop judge",
    )
    args = parser.parse_args()
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
                self.forward("GET", 8765 if route == "/api/native-state" else 8766, "/state")
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
                    8766,
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
                connection = http.client.HTTPConnection("127.0.0.1", 8766, timeout=30)
                try:
                    connection.request(
                        "POST",
                        "/transcribe",
                        self.rfile.read(size),
                        {
                            "Content-Type": self.headers.get("Content-Type", "audio/webm"),
                            "X-Dume-Voice-Mode": self.headers.get("X-Dume-Voice-Mode", "request"),
                        },
                    )
                    response = connection.getresponse()
                    data = response.read()
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
    server.serve_forever()


if __name__ == "__main__":
    main()
