"""Read back generated WAVs with the existing CUDA recognizer; never dispatch tasks."""

import argparse
import json
import re
from pathlib import Path

import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--asr-url", default="http://127.0.0.1:8996")
args = parser.parse_args()
report = json.loads((args.folder / "browser.json").read_text())
rows = []


def normalized(text):
    return " ".join(re.sub(r"[^a-z0-9\s]", "", text.lower()).split())


with httpx.Client(timeout=15) as client:
    for item in report["rows"]:
        file = args.folder / "speech-audio" / f"{item['result']['generation']}.wav"
        response = client.post(args.asr_url + "/transcribe", content=file.read_bytes(),
                               headers={"Content-Type": "audio/wav",
                                        "X-Dume-Voice-Mode": "request"})
        result = response.json()
        rows.append({"id": item["id"], "expected": item["text"], "status": response.status_code,
                     "recognition": result, "normalized_exact_match": response.is_success
                     and normalized(result.get("text", "")) == normalized(item["text"])})
(args.folder / "content-readback.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps({"count": len(rows), "exact_matches": sum(
    row["normalized_exact_match"] for row in rows),
                  "errors": [row["id"] for row in rows if row["status"] != 200],
                  "devices": sorted({row["recognition"].get("device", "unavailable")
                                     for row in rows})}))
