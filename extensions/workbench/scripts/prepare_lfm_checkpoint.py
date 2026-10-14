"""Pin and verify the official LFM2.5 QAD GGUF; no inference or uploads."""

import argparse
import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path

os.environ["HF_HUB_DISABLE_XET"] = "1"
from huggingface_hub import HfApi, hf_hub_download  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--direct-http", action="store_true", help="Bypass Hub file-cache transfer")
parser.add_argument("--revision", default="0912d33141f77e10705345a6732bfd83f0252fdc",
                    help="Immutable publisher revision; defaults to the evaluated checkpoint")
args = parser.parse_args()
args.revision = args.revision.lower()
if len(args.revision) != 40 or any(c not in "0123456789abcdef" for c in args.revision):
    parser.error("--revision must be an immutable 40-character commit SHA")
args.output.mkdir(parents=True, exist_ok=True)
repo = "LiquidAI/LFM2.5-24B-A2B-GGUF"
filename = "LFM2.5-24B-A2B-QAD-Q4_0.gguf"
manifest = args.output / "preparation.json"
if manifest.exists():
    report = json.loads(manifest.read_text())
    assert report["repo"] == repo and report["filename"] == filename
    assert report["revision"] == args.revision, "Existing manifest pins a different revision"
else:
    info = HfApi().model_info(repo, revision=args.revision, files_metadata=True)
    remote = next(f for f in info.siblings if f.rfilename == filename)
    assert remote.lfs and len(remote.lfs.sha256) == 64
    report = {"repo": repo, "revision": info.sha, "filename": filename,
              "expected_bytes": remote.lfs.size, "expected_sha256": remote.lfs.sha256,
              "scope": "Anonymous public download; local verification; no model evaluation yet"}
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
report.pop("verified", None)
manifest.write_text(json.dumps(report, indent=2) + "\n")
if shutil.disk_usage(args.output).free < report["expected_bytes"] * 2:
    raise RuntimeError("Insufficient free disk for download and preserved import copy")
local = args.output / "checkpoint"
for name in ("LICENSE", "README.md", filename):
    if name == filename and args.direct_http:
        path = local / filename
        partial = local / (filename + ".http.partial")
        offset = partial.stat().st_size if partial.exists() else 0
        assert offset <= report["expected_bytes"]
        if not path.exists() and offset < report["expected_bytes"]:
            with partial.open("ab") as stream:
                last_notice = offset
                while offset < report["expected_bytes"]:
                    end = min(offset + 32 * 1024 * 1024, report["expected_bytes"]) - 1
                    url = (f"https://huggingface.co/{repo}/resolve/{report['revision']}/{filename}"
                           f"?download=true&offset={offset}")
                    request = urllib.request.Request(
                        url, headers={"Range": f"bytes={offset}-{end}"})
                    with urllib.request.urlopen(request, timeout=30) as response:
                        assert response.status == 206
                        assert response.headers["Content-Range"] == (
                            f"bytes {offset}-{end}/{report['expected_bytes']}"
                        )
                        block = response.read()
                        assert len(block) == end-offset+1, "Incomplete range retained"
                        stream.write(block)
                        offset += len(block)
                        assert offset <= report["expected_bytes"]
                        if offset - last_notice >= 256 * 1024 * 1024:
                            stream.flush()
                            print(f"HTTP bytes: {offset}/{report['expected_bytes']}", flush=True)
                            last_notice = offset
            assert offset == report["expected_bytes"]
        if not path.exists():
            partial.replace(path)
    else:
        path = Path(hf_hub_download(repo, name, revision=report["revision"], local_dir=local))
    assert path.resolve().is_relative_to(local.resolve())
    if name == filename:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        assert path.stat().st_size == report["expected_bytes"]
        assert digest.hexdigest() == report["expected_sha256"]
        report.update(verified=True, local_path=str(path.resolve()),
                      license_sha256=hashlib.sha256((local / "LICENSE").read_bytes()).hexdigest())
        manifest.write_text(json.dumps(report, indent=2) + "\n")
        print("Pinned official GGUF SHA-256 and byte count verified", flush=True)
