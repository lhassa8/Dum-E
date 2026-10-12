"""Fetch checksum-pinned browser VAD assets. No audio or microphone access."""

import argparse
import base64
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "vad-web": (
        "https://registry.npmjs.org/@ricky0123/vad-web/-/vad-web-0.0.31.tgz",
        "ePVq8TvB21sdHSxVMZOEIf9JVa7MAYpaIaNXeGgsPOiMCN8xbPCdF2LS5aYj7VRR3ZxzutedgV9ZplV65IA1Fg==",
    ),
    "onnxruntime-web": (
        "https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.22.0.tgz",
        "Ud/+EBo6mhuaQWt/OjaOk0iNWjXqJoeeMFr6xQEERZdIZH2OWpGzuujz7lfuOBjUa6TEE/sc4nb7Da5dNL34fg==",
    ),
}


def prepare(destination):
    specification = ROOT / "integrations/speech-vad"
    assets = json.loads((specification / "assets.json").read_text())
    destination.mkdir(parents=True, exist_ok=True)
    for package, (url, integrity) in PACKAGES.items():
        selected = {name: spec for name, spec in assets.items() if spec["package"] == package}
        if all(
            (destination / name).is_file()
            and hashlib.sha256((destination / name).read_bytes()).hexdigest() == spec["sha256"]
            for name, spec in selected.items()
        ):
            continue
        archive = urllib.request.urlopen(url, timeout=60).read()
        if base64.b64encode(hashlib.sha512(archive).digest()).decode() != integrity:
            raise ValueError(f"Registry integrity mismatch: {package}")
        # Read only named regular files; never extract arbitrary archive paths.
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for name, spec in selected.items():
                member = tar.getmember(f"package/dist/{name}")
                if not member.isfile():
                    raise ValueError(f"Not a regular asset: {name}")
                data = tar.extractfile(member).read()
                if len(data) != spec["bytes"] or hashlib.sha256(data).hexdigest() != spec["sha256"]:
                    raise ValueError(f"Asset checksum mismatch: {name}")
                temporary = destination / f".{name}.partial"
                temporary.write_bytes(data)
                temporary.replace(destination / name)
    for license_file in (specification / "licenses").iterdir():
        (destination / license_file.name).write_bytes(license_file.read_bytes())
    (destination / "assets.json").write_text(json.dumps(assets, indent=2) + "\n")
    print("Verified local speech detector assets:", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/speech-vad")
    prepare(parser.parse_args().output.resolve())
