"""Record real loopback LIBERO camera frames; never submit robot commands."""

import argparse
import io
import json
import time
import urllib.request
from pathlib import Path

import imageio
import numpy as np
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--seconds", type=float, default=40)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
started = time.monotonic()
timestamps = []
with imageio.get_writer(str(args.output / "camera.mp4"), fps=10) as writer:
    while time.monotonic() - started < args.seconds:
        tick = time.monotonic()
        with urllib.request.urlopen("http://127.0.0.1:8901/frame.jpg", timeout=5) as response:
            frame = response.read()
        if frame:
            writer.append_data(np.array(Image.open(io.BytesIO(frame)).convert("RGB")))
            timestamps.append(time.monotonic() - started)
        time.sleep(max(0, 0.1 - (time.monotonic() - tick)))
(args.output / "timestamps.json").write_text(
    json.dumps(
        {
            "wall_seconds": time.monotonic() - started,
            "frame_wall_seconds": timestamps,
            "playback_fps": 10,
            "source": "Actual LIBERO loopback camera, sampled independently; no motion commands",
        }
    )
    + "\n"
)
