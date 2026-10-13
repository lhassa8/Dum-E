"""Evaluate an installed Strands runtime; this is not a learned manipulation demo.

Run in an isolated environment containing strands-robots[sim-mujoco].
The Panda asset is the existing workbench asset, with no edits or downloads.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from strands_robots.policies import Policy
from strands_robots.simulation import create_simulation


class SmallJointMotion(Policy):
    reads_instruction = False
    instruction_free_actions = "bounded joint-one motion for an execution-contract probe"

    def __init__(self):
        self.keys = []
        self.initial = None
        self.calls = 0

    def set_robot_state_keys(self, robot_state_keys):
        self.keys = list(robot_state_keys)
        expected = [f"actuator{i}" for i in range(1, 9)]
        if self.keys != expected:
            raise ValueError(f"Unexpected Panda asset action schema: {self.keys}")

    @property
    def requires_images(self):
        return False

    @property
    def provider_name(self):
        return "workbench_runtime_probe"

    async def get_actions(self, observation_dict, instruction, **kwargs):
        if self.initial is None:
            self.initial = {
                f"actuator{i}": float(observation_dict[f"joint{i}"]) for i in range(1, 8)
            }
            # This asset's split-tendon actuator uses 0..255, not finger metres.
            # Keep the already-open hand open; this probe carries no objects.
            fingers = [float(observation_dict[f"finger_joint{i}"]) for i in (1, 2)]
            if not all(np.isfinite(v) and 0.035 <= v <= 0.041 for v in fingers):
                raise ValueError(f"Expected the asset's open home hand, got {fingers}")
            self.initial["actuator8"] = 255.0
        self.calls += 1
        action = dict(self.initial)
        action["actuator1"] += min(self.calls * 0.01, 0.10)
        return [action]


def check(result):
    if result["status"] != "success":
        raise RuntimeError(json.dumps(result, default=str))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    asset = (
        Path(__file__).resolve().parents[1] / "src/physical_ai_lab/assistant/assets/panda/panda.xml"
    )
    actuators = ET.parse(asset).getroot().find("actuator")
    assert actuators is not None
    arm_map = {a.attrib["name"]: a.attrib.get("joint") for a in actuators}
    assert all(arm_map[f"actuator{i}"] == f"joint{i}" for i in range(1, 8))
    gripper = next(a for a in actuators if a.attrib["name"] == "actuator8")
    assert gripper.attrib["tendon"] == "split" and gripper.attrib["ctrlrange"] == "0 255"
    report = {
        "source_revision": args.source_revision,
        "rendering": "software llvmpipe reported by framework; no GPU rendering claim",
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("strands-robots", "strands-agents", "mujoco", "numpy")
        },
        "asset_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
        "scope": (
            "real MuJoCo joint execution and cooperative cancellation; "
            "no grasp or pretrained policy"
        ),
        "trials": [],
    }
    try:
        for trial in range(3):
            sim = create_simulation("mujoco")
            events = []
            started_motion = threading.Event()
            ended = threading.Event()

            def observer(event):
                events.append((time.perf_counter(), event))
                if type(event).__name__ == "RunPolicyStep" and len(events) >= 9:
                    started_motion.set()
                if type(event).__name__ == "RunPolicyEnded":
                    ended.set()

            try:
                check(sim.create_world(timestep=0.002))
                check(sim.add_robot(name="panda", urdf_path=str(asset), keyframe="home"))
                keys = sim.robot_action_keys("panda")
                state_keys = [f"joint{i}" for i in range(1, 8)] + ["finger_joint1", "finger_joint2"]
                before = sim.get_observation("panda", skip_images=True)
                if trial == 0:
                    import cv2

                    images = sim.get_observation("panda")
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    for name, value in images.items():
                        if isinstance(value, np.ndarray) and value.ndim == 3:
                            path = args.output.parent / f"before-{name}.png"
                            assert cv2.imwrite(str(path), cv2.cvtColor(value, cv2.COLOR_RGB2BGR))
                check(
                    sim.start_policy(
                        robot_name="panda",
                        policy_object=SmallJointMotion(),
                        instruction="runtime probe",
                        n_steps=1000,
                        reset_between=False,
                        control_frequency=50.0,
                        action_horizon=1,
                        observer=observer,
                    )
                )
                if not started_motion.wait(10):
                    raise RuntimeError("No eight applied actions observed within ten seconds")
                requested = time.perf_counter()
                stop_result = sim.stop_policy("panda")
                if not ended.wait(10):
                    raise RuntimeError("No terminal observer event after cancellation")
                after = sim.get_observation("panda", skip_images=True)
                terminal_t, terminal = next(
                    (t, e) for t, e in events if type(e).__name__ == "RunPolicyEnded"
                )
                applied = [e for _, e in events if type(e).__name__ == "RunPolicyStep"]
                q0 = np.array([float(before[k]) for k in state_keys])
                q1 = np.array([float(after[k]) for k in state_keys])
                assert np.isfinite(q1).all()
                assert abs(float(after["joint1"]) - float(before["joint1"])) > 0.005
                assert terminal.stopped_reason == "cancelled", str(terminal)
                assert not any(
                    type(e).__name__ == "RunPolicyStep" and t > terminal_t for t, e in events
                )
                check(sim.step(500))
                settled = sim.get_observation("panda", skip_images=True)
                if trial == 0:
                    images = sim.get_observation("panda")
                    for name, value in images.items():
                        if isinstance(value, np.ndarray) and value.ndim == 3:
                            path = args.output.parent / f"after-{name}.png"
                            assert cv2.imwrite(str(path), cv2.cvtColor(value, cv2.COLOR_RGB2BGR))
                drift = max(abs(float(settled[k]) - float(after[k])) for k in state_keys)
                report["trials"].append(
                    {
                        "trial": trial,
                        "action_keys": keys,
                        "applied_actions": len(applied),
                        "stop_to_terminal_ms": (terminal_t - requested) * 1000,
                        "joint1_displacement_rad": float(after["joint1"]) - float(before["joint1"]),
                        "max_state_change": float(np.max(np.abs(q1 - q0))),
                        "post_cancel_1s_sim_drift": drift,
                        "stopped_reason": terminal.stopped_reason,
                        "within_existing_0_02_rad_hold_bound_at_1s": drift < 0.02,
                        "stop_response": stop_result,
                    }
                )
            finally:
                sim.cleanup()
        report["passed"] = True
        report["workbench_stop_qualified"] = False
        report["qualification_note"] = (
            "No tool, 1s diagnostic only; original 32s/tool hold qualification not run. "
            "Drift exceeding 0.02 rad already contradicts the joint hold bound."
        )
    except Exception as exc:
        report["passed"] = False
        report["error"] = repr(exc)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
