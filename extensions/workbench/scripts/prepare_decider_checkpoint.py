"""Download immutable public Decider/base revisions and verify artifact hashes."""

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
repo = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"
revision = "216d1ccb46a9e9b036eb9187b248db98480f77d4"
checkpoint = Path(
    snapshot_download(
        repo,
        revision=revision,
        allow_patterns=[
            "*.json",
            "*.safetensors",
            "*.jinja",
            "LICENSE.md",
            "MANIFEST.sha256",
            "README.md",
            "lora/*",
        ],
        ignore_patterns=["eval/*", "training/*"],
        max_workers=4,
    )
)
config = json.loads((checkpoint / "strands_decider_config.json").read_text())
provenance = json.loads((checkpoint / "provenance.json").read_text())
base_repo = config["base_model"]
assert base_repo == provenance["base_model"]
base_revision = provenance["base_model_revision"]
base = Path(
    snapshot_download(
        base_repo,
        revision=base_revision,
        allow_patterns=["*.json", "*.safetensors", "*.jinja", "LICENSE*", "README.md"],
        max_workers=4,
    )
)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


files = {}
for prefix, folder in (("checkpoint", checkpoint), ("base", base)):
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            files[prefix + "/" + str(path.relative_to(folder))] = {
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
assert files["checkpoint/head.safetensors"]["sha256"] == provenance["head_sha256"]
assert files["checkpoint/lora/adapter_model.safetensors"]["sha256"] == provenance["adapter_sha256"]
base_metadata = HfApi().model_info(base_repo, revision=base_revision, files_metadata=True)
base_verified = []
for remote in base_metadata.siblings:
    key = "base/" + remote.rfilename
    if key in files and remote.lfs is not None:
        assert files[key]["sha256"] == remote.lfs.sha256, remote.rfilename
        assert files[key]["bytes"] == remote.lfs.size, remote.rfilename
        base_verified.append(remote.rfilename)
assert any(name.endswith(".safetensors") for name in base_verified)
report = {
    "repo": repo,
    "revision": revision,
    "checkpoint_path": str(checkpoint),
    "base_repo": base_repo,
    "base_revision": base_revision,
    "base_path": str(base),
    "base_lfs_hashes_verified": base_verified,
    "provenance": provenance,
    "files": files,
}
(args.output / "checkpoint-identity.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "files"}, indent=2))
