"""Record rendered localhost simulator frames; no camera or microphone access."""

import argparse
import subprocess
import time
from pathlib import Path

import httpx

from physical_ai_lab.dume.asr import ffmpeg_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--url", default="http://127.0.0.1:8876")
parser.add_argument("--seconds", type=float, default=45)
args = parser.parse_args()
if args.seconds <= 0 or args.output.exists():
    parser.error("Use a fresh output path and positive duration")
args.output.parent.mkdir(parents=True, exist_ok=True)
encoder = subprocess.Popen(
    [
        ffmpeg_path(),
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-framerate",
        "4",
        "-i",
        "pipe:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(args.output),
    ],
    stdin=subprocess.PIPE,
)
frames = 0
started = time.monotonic()
try:
    with httpx.Client(base_url=args.url, trust_env=False, timeout=5) as client:
        while time.monotonic() - started < args.seconds:
            response = client.get("/frame.jpg")
            response.raise_for_status()
            encoder.stdin.write(response.content)
            frames += 1
            time.sleep(max(0, started + frames / 4 - time.monotonic()))
finally:
    encoder.stdin.close()
    if encoder.wait(timeout=15):
        raise RuntimeError("Simulator video encoding failed")
print(f"Recorded {frames} actual rendered frames: {args.output}")
