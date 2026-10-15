"""Resume and verify only the three pinned public LIBERO HDF5 demonstration files."""

import argparse
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("metadata", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
selected = json.loads(args.metadata.read_text())
assert selected["repo"] == "yifengzhu-hf/LIBERO-datasets"
assert selected["revision"] == "f13aa24a3da8c43c7225569f28c562979fa0e35a"
assert selected["license"] == "apache-2.0" and len(selected["files"]) == 3
args.output.mkdir(parents=True, exist_ok=True)
assert shutil.disk_usage(args.output).free > sum(f["size"] for f in selected["files"])*2
manifest = args.output/"preparation.json"
if manifest.exists():
    previous = json.loads(manifest.read_text())
    assert previous["revision"] == selected["revision"] and previous["repo"] == selected["repo"]
report = {"repo": selected["repo"], "revision": selected["revision"],
          "license": selected["license"], "files": [], "verified": False}
(args.output/"selected-files.json").write_bytes(args.metadata.read_bytes())
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
manifest.write_text(json.dumps(report, indent=2)+"\n")
for spec in selected["files"]:
    name = spec["rfilename"]
    assert name.startswith("libero_spatial/") and name.endswith("_demo.hdf5")
    path = args.output/name
    assert path.resolve().is_relative_to(args.output.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    size, expected = spec["lfs"]["size"], spec["lfs"]["sha256"]
    assert size == spec["size"] and len(expected) == 64
    partial = path.with_suffix(".hdf5.partial")
    if not path.exists():
        offset = partial.stat().st_size if partial.exists() else 0
        assert offset <= size
        with partial.open("ab") as stream:
            while offset < size:
                end = min(offset+32*1024*1024, size)-1
                url = (f"https://huggingface.co/datasets/{selected['repo']}/resolve/"
                       f"{selected['revision']}/{name}?download=true&offset={offset}")
                for attempt in range(3):
                    try:
                        request = urllib.request.Request(
                            url, headers={"Range": f"bytes={offset}-{end}"})
                        with urllib.request.urlopen(request, timeout=30) as response:
                            assert response.status == 206
                            expected_range = f"bytes {offset}-{end}/{size}"
                            assert response.headers["Content-Range"] == expected_range
                            block = response.read(end-offset+2)
                            assert len(block) == end-offset+1
                        break
                    except (OSError, AssertionError):
                        if attempt == 2:
                            raise
                        time.sleep(.5)
                stream.write(block)
                stream.flush()
                offset += len(block)
                print(json.dumps({"file": path.name, "bytes": offset, "total": size}), flush=True)
        partial.replace(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    assert path.stat().st_size == size and digest.hexdigest() == expected
    report["files"].append({"name": name, "bytes": size, "sha256": expected})
    manifest.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"file": path.name, "verified": True}), flush=True)
report["verified"] = True
manifest.write_text(json.dumps(report, indent=2)+"\n")
