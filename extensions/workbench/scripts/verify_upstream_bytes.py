"""Verify attribution bytes; optionally undo only proven Windows CRLF conversion."""

import argparse
import hashlib
import json
from pathlib import Path

from physical_ai_lab.dume.upstream import VENDOR

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--restore-lf", action="store_true")
args = parser.parse_args()
manifest = json.loads((Path(__file__).resolve().parents[1] / "upstream-source.json").read_text())
restored = []
for name, expected in manifest["files"].items():
    path = VENDOR / name
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() == expected:
        continue
    original = data.replace(b"\r\n", b"\n")
    if not args.restore_lf or hashlib.sha256(original).hexdigest() != expected:
        raise RuntimeError(f"Protected upstream file differs: {name}; no changes made to it")
    path.write_bytes(original)
    restored.append(name)
print(f"Verified {len(manifest['files'])} upstream files; restored LF in {len(restored)}.")
