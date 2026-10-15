"""Prepare actual pre-action supervision from qualified interrupted native replays."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
parser.add_argument("inspection", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
assert not args.output.exists()
report = json.loads((args.run/"report.json").read_text())
audit = json.loads((args.run/"audit.json").read_text())
inspection = json.loads((args.inspection/"report.json").read_text())
assert audit["audit_completed"] and report["protocol"]["interrupt_enabled"]
assert len(report["episodes"]) == len(audit["episodes"]) == len(report["protocol"]["cases"])
windows, chunks, sources, excluded = [], [], [], []
for result, qualified in zip(report["episodes"], audit["episodes"]):
    assert all(result[k] == qualified[k] for k in ("task_id", "demo"))
    if not qualified.get("interrupted_journey_passed", False):
        excluded.append({"task_id": result["task_id"], "demo": result["demo"]})
        continue
    task = next(t for t in inspection["tasks"] if t["task_id"] == result["task_id"])
    identity = next(d for d in task["episodes"] if d["demo"] == result["demo"])
    assert not identity["excluded_state_overlap"]
    prompt = task["file"].replace("_demo.hdf5", "").replace("_", " ")
    directory = args.run/f"task{result['task_id']}-{result['demo']}"
    rows = json.loads((directory/"actions.json").read_text())
    native = np.asarray([r["action"] for r in rows], dtype=np.float32)
    assert native.shape == (result["active_steps"], 7) and np.isfinite(native).all()
    insertion = result["hold_insertion_index"]
    for begin, end in ((0, insertion), (insertion, len(rows))):
        for start in range(begin, end-7):
            path = directory/"observations"/f"{start:04d}.npz"
            with np.load(path, allow_pickle=False) as raw:
                assert set(raw.files) == {"agentview_image", "robot0_eye_in_hand_image",
                                          "robot0_eef_pos", "robot0_eef_quat",
                                          "robot0_gripper_qpos"}
            windows.append({"task_id": result["task_id"], "demo": result["demo"],
                            "segment_start": begin, "segment_end_exclusive": end,
                            "action_start": start, "action_end_exclusive": start+8,
                            "observation": str(path.resolve()), "task_prompt": prompt,
                            "observation_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            chunks.append(native[start:start+8])
    sources.append({"task_id": result["task_id"], "demo": result["demo"],
                    "actions_sha256": hashlib.sha256((directory/"actions.json").read_bytes()
                                                       ).hexdigest(),
                    "active_steps": len(rows)})
assert sources and {s["task_id"] for s in sources} == {0, 1, 2}, "All three tasks required"
args.output.mkdir(parents=True, exist_ok=False)
np.savez(args.output/"targets-native-osc.npz", actions=np.stack(chunks))
(args.output/"source-audit.json").write_bytes((args.run/"audit.json").read_bytes())
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
manifest = {"status": "Training candidate only; actual native pre-action observations",
            "scope": "Qualified human-action replay supervision; no learned-policy result",
            "horizon": 8, "padding": False, "crosses_explicit_pause": False,
            "normalization": "None; publisher conversion/statistics applied separately",
            "target_sha256": hashlib.sha256(
                (args.output/"targets-native-osc.npz").read_bytes()).hexdigest(),
            "source_audit_sha256": hashlib.sha256((args.run/"audit.json").read_bytes()).hexdigest(),
            "episode_sources": sources, "excluded_episodes": excluded, "windows": windows}
(args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(json.dumps({"episodes": len(sources), "excluded": len(excluded), "chunks": len(chunks)}))
