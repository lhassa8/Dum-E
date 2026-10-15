"""Merge independently qualified supervision without duplicate source episodes."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("datasets", nargs="+", type=Path)
args = parser.parse_args()
assert not args.output.exists()
windows, targets, episodes, excluded, provenance = [], [], [], [], []
seen = set()
for directory in args.datasets:
    path = directory/"manifest.json"
    manifest = json.loads(path.read_text())
    audit_path = directory/"source-audit.json"
    assert hashlib.sha256(audit_path.read_bytes()).hexdigest() == manifest["source_audit_sha256"]
    audit = json.loads(audit_path.read_text())
    assert audit["audit_completed"]
    assert not manifest["padding"] and not manifest["crosses_explicit_pause"]
    target_path = directory/"targets-native-osc.npz"
    assert hashlib.sha256(target_path.read_bytes()).hexdigest() == manifest["target_sha256"]
    with np.load(target_path, allow_pickle=False) as data:
        values = data["actions"]
    assert values.shape == (len(manifest["windows"]), 8, 7) and np.isfinite(values).all()
    for entry in manifest["episode_sources"]+manifest["excluded_episodes"]:
        key = (entry["task_id"], entry["demo"])
        assert key not in seen, "Repeated source episode cannot be counted as new supervision"
        seen.add(key)
    qualified = {(e["task_id"], e["demo"]) for e in audit["episodes"]
                 if e.get("interrupted_journey_passed", False)}
    assert {(e["task_id"], e["demo"]) for e in manifest["episode_sources"]} == qualified
    assert all((w["task_id"], w["demo"]) in qualified for w in manifest["windows"])
    windows.extend(manifest["windows"])
    targets.append(values)
    episodes.extend(manifest["episode_sources"])
    excluded.extend(manifest["excluded_episodes"])
    provenance.append({"directory": str(directory.resolve()),
                       "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert {e["task_id"] for e in episodes} == {0, 1, 2}
args.output.mkdir(parents=True, exist_ok=False)
np.savez(args.output/"targets-native-osc.npz", actions=np.concatenate(targets))
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
manifest = {"status": "Merged qualified human-action supervision; no model qualification",
            "horizon": 8, "padding": False, "crosses_explicit_pause": False,
            "target_sha256": hashlib.sha256(
                (args.output/"targets-native-osc.npz").read_bytes()).hexdigest(),
            "source_datasets": provenance, "episode_sources": episodes,
            "excluded_episodes": excluded, "windows": windows}
(args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(json.dumps({"episodes": len(episodes), "excluded": len(excluded), "windows": len(windows)}))
