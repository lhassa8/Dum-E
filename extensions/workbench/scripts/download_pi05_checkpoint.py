# /// script
# requires-python = ">=3.12"
# dependencies = ["google-crc32c==1.7.1"]
# ///
"""Download official weights, pinning object generations and verifying GCS CRC32C."""

import argparse
import base64
import hashlib
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import google_crc32c

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
prefix = "checkpoints/pi05_libero/"
url = "https://storage.googleapis.com/storage/v1/b/openpi-assets/o?" + urllib.parse.urlencode(
    {"prefix": prefix, "maxResults": 1000}
)
listing = json.load(urllib.request.urlopen(url, timeout=30))
if listing.get("nextPageToken") or not listing.get("items"):
    raise RuntimeError("Unexpected checkpoint listing; preserve evidence and inspect")
args.output.mkdir(parents=True, exist_ok=True)
manifest_path = args.output / "checkpoint-objects.json"
if manifest_path.exists():
    if json.loads(manifest_path.read_text()) != listing:
        raise RuntimeError("Remote checkpoint metadata changed; use a separate experiment")
else:
    manifest_path.write_text(json.dumps(listing, indent=2) + "\n")


def download(obj):
    relative = Path(obj["name"].removeprefix(prefix))
    if relative.is_absolute() or ".." in relative.parts or "crc32c" not in obj:
        raise RuntimeError("Unsafe or unverifiable checkpoint object")
    path = args.output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    hash_path = args.output.parent / (args.output.name + "-sha256") / relative
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data_hash = google_crc32c.Checksum()
        with path.open("rb") as existing:
            for block in iter(lambda: existing.read(8 * 1024 * 1024), b""):
                data_hash.update(block)
        if (
            path.stat().st_size == int(obj["size"])
            and base64.b64encode(data_hash.digest()).decode() == obj["crc32c"]
        ):
            return str(relative)
        raise RuntimeError(f"Existing checkpoint file fails integrity: {relative}")
    partial = path.with_name(path.name + ".partial")
    media_url = "https://storage.googleapis.com/download/storage/v1/b/openpi-assets/o/"
    media_url += urllib.parse.quote(obj["name"], safe="")
    media_url += "?" + urllib.parse.urlencode({"alt": "media", "generation": obj["generation"]})
    checksum = google_crc32c.Checksum()
    sha = hashlib.sha256()
    with urllib.request.urlopen(media_url, timeout=60) as response, partial.open("wb") as output:
        for block in iter(lambda: response.read(8 * 1024 * 1024), b""):
            checksum.update(block)
            sha.update(block)
            output.write(block)
    if (
        partial.stat().st_size != int(obj["size"])
        or base64.b64encode(checksum.digest()).decode() != obj["crc32c"]
    ):
        raise RuntimeError(f"Downloaded checkpoint failed integrity: {relative}")
    partial.replace(path)
    hash_path.write_text(sha.hexdigest() + "\n")
    print(f"Verified {relative}: {obj['size']} bytes", flush=True)
    return str(relative)


with ThreadPoolExecutor(max_workers=3) as pool:
    files = list(pool.map(download, listing["items"]))
# Keep integrity notes outside Orbax's checkpoint tree. Older preparations wrote
# sidecars alongside arrays; preserve and relocate those rather than feeding
# extra process metadata files to the upstream checkpoint reader.
hash_root = (args.output.parent / (args.output.name + "-sha256")).resolve()
for sidecar in args.output.rglob("*.sha256"):
    digest = sidecar.read_text().strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RuntimeError("Unexpected checksum sidecar; inspect without altering it")
    target = hash_root / sidecar.relative_to(args.output).with_suffix("")
    if not target.resolve().is_relative_to(hash_root):
        raise RuntimeError("Checksum target escaped its output directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != sidecar.read_bytes():
        raise RuntimeError("Conflicting checksum history; no overwrite")
    sidecar.replace(target)
print(f"Verified {len(files)} official checkpoint objects at {args.output}", flush=True)
