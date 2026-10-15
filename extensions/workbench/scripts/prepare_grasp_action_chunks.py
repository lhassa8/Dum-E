"""Prepare full, unpadded teacher action chunks; no model loading or training."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
assert not args.output.exists(), "Use a fresh dataset directory"
report = json.loads((args.run/"report.json").read_text())
audit = json.loads((args.run/"audit.json").read_text())
assert audit.get("audit_completed", audit["passed"]) and audit["complete_placement"]
assert report["complete_placement_requested"]
assert len(report["episodes"]) == len(audit["episodes"])
chunks, windows, sources, excluded = [], [], [], []
for episode, verified in zip(report["episodes"], audit["episodes"]):
    for key in ("task_id", "initial_state_index"):
        assert episode[key] == verified[key]
    if not verified.get("passed", audit["passed"]):
        excluded.append({"task_id": episode["task_id"],
                         "initial_state_index": episode["initial_state_index"],
                         "error": episode["error"]})
        continue
    assert episode["complete_teacher_passed"] and episode["error"] is None
    assert episode["initial_state_index"] in report["protocol"]["state_split"][
        "training_and_teacher_calibration"]
    directory = args.run/f"task{episode['task_id']}-state{episode['initial_state_index']}"
    actions_path = directory/"actions.json"
    rows = json.loads(actions_path.read_text())
    actions = np.asarray([r["action"] for r in rows], dtype=np.float32)
    assert actions.shape == (episode["active_steps"], 7) and np.isfinite(actions).all()
    assert np.abs(actions).max() <= 1+1e-7
    assert np.isin(actions[:, -1], [-1., 1.]).all()
    insertion = episode["hold_insertion_index"]
    # The explicit pause is not an eight-action trajectory interval. Keep
    # separate contiguous segments and discard incomplete trailing windows.
    for begin, end in ((0, insertion), (insertion, len(rows))):
        for index in range(begin, end-8+1):
            path = directory/"observations"/f"{index:04d}.npz"
            with np.load(path, allow_pickle=False) as raw:
                assert set(raw.files) == {"agentview_image", "robot0_eye_in_hand_image",
                                          "robot0_eef_pos", "robot0_eef_quat",
                                          "robot0_gripper_qpos"}
            windows.append({"task_id": episode["task_id"],
                            "initial_state_index": episode["initial_state_index"],
                            "segment_start": begin, "segment_end_exclusive": end,
                            "action_start": index, "action_end_exclusive": index+8,
                            "observation": str(path.resolve()),
                            "observation_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "task_prompt": episode["task_prompt"]})
            chunks.append(actions[index:index+8])
    sources.append({"actions_sha256": hashlib.sha256(actions_path.read_bytes()).hexdigest(),
                    "task_id": episode["task_id"],
                    "initial_state_index": episode["initial_state_index"],
                    "active_steps": len(rows)})
assert chunks
args.output.mkdir(parents=True, exist_ok=False)
(args.output/"source-audit.json").write_bytes((args.run/"audit.json").read_bytes())
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
targets = args.output/"targets-native-osc.npz"
np.savez(targets, actions=np.stack(chunks))
manifest = {"status": "Prepared training-only labels; no learned weights or qualification",
            "action_contract": "Original native7D OSC; gripper+1 closed/-1 open; not joint targets",
            "horizon": 8, "padding": False, "crosses_explicit_pause": False,
            "normalization": "None; apply publisher gripper inverse and action stats later",
            "source_audit_sha256": hashlib.sha256((args.run/"audit.json").read_bytes()).hexdigest(),
            "target_sha256": hashlib.sha256(targets.read_bytes()).hexdigest(),
            "preparation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "episode_sources": sources, "excluded_episodes": excluded, "windows": windows}
(args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(json.dumps({"episodes": len(sources), "excluded": len(excluded), "chunks": len(chunks),
                  "shape": list(np.stack(chunks).shape), "trained": False}))
