"""Download and verify the pinned public OpenVLA-OFT spatial inference checkpoint."""

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from huggingface_hub import HfApi

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--only-file",
                    help="Repair one publisher file; never qualifies a full checkpoint")
args = parser.parse_args()
repo = "moojink/openvla-7b-oft-finetuned-libero-spatial"
revision = "6d0231af0e48c5985f1ff86908f4674b84bc049b"
args.output.mkdir(parents=True, exist_ok=True)
manifest = args.output/"preparation.json"
info = HfApi(token=False).model_info(repo, revision=revision, files_metadata=True)
assert info.sha == revision and not info.gated
files = [{"name": f.rfilename, "bytes": f.size,
          "sha256": f.lfs.sha256 if f.lfs else None, "git_blob_sha1": f.blob_id}
         for f in info.siblings if "/" not in f.rfilename and f.rfilename != ".gitattributes"]
report = {"repo": repo, "revision": revision, "license_metadata": info.card_data.get("license"),
          "files": files, "scope": "Public inference files only; no uploads or inference"}
if manifest.exists():
    old = json.loads(manifest.read_text())
    assert old["repo"] == repo and old["revision"] == revision and old["files"] == files
selected = [f for f in files if not args.only_file or f["name"] == args.only_file]
assert selected and (not args.only_file or len(selected) == 1)
assert shutil.disk_usage(args.output).free > sum(f["bytes"] for f in selected)*1.2
report["selection"] = [f["name"] for f in selected]
manifest.write_text(json.dumps(report, indent=2)+"\n")
local = args.output/"checkpoint"
local.mkdir(exist_ok=True)


def download(spec):
    name = spec["name"]
    destination = local/name
    assert destination.resolve().is_relative_to(local.resolve())
    partial = local/(name+".partial")
    if not destination.exists():
        offset = partial.stat().st_size if partial.exists() else 0
        assert offset <= spec["bytes"]
        with partial.open("ab") as stream:
            last_notice = offset
            while offset < spec["bytes"]:
                end = min(offset+32*1024*1024, spec["bytes"])-1
                url = (f"https://huggingface.co/{repo}/resolve/{revision}/{name}"
                       f"?download=true&offset={offset}")
                ranged = spec["bytes"] > 32*1024*1024
                block_path, header_path = local/(name+".range"), local/(name+".headers")
                command = ["curl", "--fail", "--location", "--silent", "--show-error",
                           "--max-time", "30", "--retry", "2", "--retry-all-errors",
                           "--retry-max-time", "60", "--output", str(block_path),
                           "--dump-header", str(header_path), "--write-out", "%{http_code}"]
                if ranged:
                    command.extend(["--range", f"{offset}-{end}"])
                response = subprocess.run(command+[url], capture_output=True, text=True, check=True)
                if ranged:
                    assert response.stdout == "206"
                    expected_range = f"content-range: bytes {offset}-{end}/{spec['bytes']}"
                    assert expected_range in header_path.read_text().lower().splitlines()
                else:
                    assert offset == 0 and response.stdout == "200"
                assert block_path.stat().st_size == end-offset+1
                with block_path.open("rb") as block_stream:
                    shutil.copyfileobj(block_stream, stream)
                offset = end+1
                block_path.unlink()
                header_path.unlink()
                stream.flush()
                if offset-last_notice >= 512*1024*1024:
                    print(f"{name}: {offset}/{spec['bytes']} bytes", flush=True)
                    last_notice = offset
        partial.replace(destination)
    assert destination.stat().st_size == spec["bytes"]
    sha256 = hashlib.sha256()
    blob = hashlib.sha1(f"blob {spec['bytes']}\0".encode())
    with destination.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            sha256.update(block)
            if not spec["sha256"]:
                blob.update(block)
    if spec["sha256"]:
        assert sha256.hexdigest() == spec["sha256"], name
    else:
        assert blob.hexdigest() == spec["git_blob_sha1"], name
    print(f"Verified {name}", flush=True)
    return {"name": name, "bytes": spec["bytes"], "local_sha256": sha256.hexdigest()}


verified, errors = [], {}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(download, spec): spec["name"] for spec in selected}
    for future in concurrent.futures.as_completed(futures):
        try:
            verified.append(future.result())
        except Exception as caught:
            name = futures[future]
            errors[name] = {"type": type(caught).__name__,
                            "returncode": getattr(caught, "returncode", None)}
            print(json.dumps({"file": name, "error": errors[name]}), flush=True)
report.update(verified=not errors and not args.only_file, subset_verified=not errors,
              verified_files=sorted(verified, key=lambda f: f["name"]), failed_files=errors,
              local_path=str(local.resolve()))
manifest.write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({"verified": report["verified"], "subset_verified": not errors,
                  "files": len(verified),
                  "verified_bytes": sum(f["bytes"] for f in verified)}))
if errors:
    raise SystemExit("Failed files retained; checkpoint is not qualified")
