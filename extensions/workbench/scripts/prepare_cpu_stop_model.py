"""Pin and verify a public local CPU Stop-recognizer checkpoint; never upload audio."""

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

MODEL = "Systran/faster-whisper-tiny.en"
REVISION = "0d3d19a32d3338f10357c0889762bd8d64bbdeba"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
info = HfApi(token=False).model_info(MODEL, revision=REVISION, files_metadata=True)
assert info.sha == REVISION
names = {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "README.md"}
files = []
for entry in info.siblings:
    if entry.rfilename in names:
        files.append({"file": entry.rfilename, "size": entry.size, "git_blob": entry.blob_id,
                      "lfs_sha256": entry.lfs.sha256 if entry.lfs else None})
freeze = {"model": MODEL, "revision": REVISION, "files": files,
          "device": "cpu", "compute_type": "int8", "purpose": "Experimental positive Stop only"}
(args.output / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
path = Path(snapshot_download(MODEL, revision=REVISION, token=False, allow_patterns=sorted(names)))
verified = []
for entry in files:
    data = (path / entry["file"]).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert len(data) == entry["size"], entry["file"]
    if entry["lfs_sha256"]:
        assert digest == entry["lfs_sha256"], entry["file"]
    else:
        blob = b"blob " + str(len(data)).encode() + b"\0" + data
        assert hashlib.sha1(blob).hexdigest() == entry["git_blob"], entry["file"]
    verified.append({**entry, "sha256": digest})
report = {**freeze, "files": verified, "resolved_path": str(path), "verified": True}
(args.output / "verified.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"model": MODEL, "revision": REVISION, "verified": True,
                  "bytes": sum(entry["size"] for entry in files)}))
