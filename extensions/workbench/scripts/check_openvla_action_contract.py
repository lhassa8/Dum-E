"""Compare our adapter with the pinned publisher's actual LIBERO conversion code."""

import argparse
import ast
import json
from pathlib import Path

import numpy as np
from openvla_inference_utils import native_actions

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True)
args = parser.parse_args()
scope = {"np": np}
for path, names in ((args.source/"experiments/robot/robot_utils.py",
                     {"normalize_gripper_action", "invert_gripper_action"}),
                    (args.source/"experiments/robot/libero/run_libero_eval.py",
                     {"process_action"})):
    functions = [node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(functions) == len(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), scope)
rng = np.random.default_rng(7)
for _ in range(128):
    raw = rng.uniform(-1, 1, (8, 7))
    raw[:, -1] = [0, .25, .49, .5, .51, .75, 1, 1.01]
    preserved = raw.copy()
    actual = native_actions(raw)
    expected = np.stack([scope["process_action"](row, "openvla") for row in raw])
    assert np.array_equal(actual, expected)
    assert np.array_equal(actual[:, :6], raw[:, :6])
    assert np.array_equal(raw, preserved)
    assert actual[:, -1].tolist() == [1, 1, 1, 0, -1, -1, -1, -1]
for invalid in (np.zeros((7, 7)), np.full((8, 7), np.nan), np.zeros((8, 6))):
    try:
        native_actions(invalid)
    except AssertionError:
        continue
    raise AssertionError("Malformed policy output accepted")
print(json.dumps({"passed": True, "publisher_matched_chunks": 128,
                  "malformed_outputs_rejected": 3,
                  "scope": "Publisher action conversion contract; no model or physical claim"}))
