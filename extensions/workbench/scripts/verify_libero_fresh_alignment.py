"""Frozen paired real-policy alignment experiment through continuously stepping physics."""

import argparse
import concurrent.futures
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--sim-port", type=int, default=8901)
parser.add_argument("--policy-port", type=int, default=8900)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(args.openpi.resolve() / "packages/openpi-client/src"))
from openpi_client import image_tools  # noqa: E402
from openpi_client.websocket_client_policy import WebsocketClientPolicy  # noqa: E402

base = "http://127.0.0.1:" + str(args.sim_port)


def get(route, binary=False):
    with urllib.request.urlopen(base + route, timeout=10) as response:
        data = response.read()
    return data if binary else json.loads(data)


def post(route, body):
    request = urllib.request.Request(base + route, json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(request, timeout=10))


client = WebsocketClientPolicy("127.0.0.1", args.policy_port)
metadata = client.get_server_metadata()
assert metadata.get("paired_experiment_rng") and metadata["device"].startswith("cuda")
assert metadata["checkpoint_objects_sha256"] == (
    "450f2d7b90db37ff3db84074fd9a67ba49fba05c1c482c430b1d1c5de8772084"
)
episodes = [{"task_id": task, "seed": seed, "variant": variant}
            for task in (0, 1, 2) for seed in (101, 202)
            for variant in ("baseline", "x+3mm")]
protocol = {
    "scope": "Fresh checkpoint inference and native physics; no voice or hardware",
    "episodes": episodes, "suite": "libero_spatial", "simulator_seed": 7,
    "initial_state_index": 0, "replan_steps": 5, "max_active_steps": 220,
    "correction": "Once on first positive gripper action: add0.06 to OSC world-X input",
    "difference_from_replay": "First closing command, rather than preceding open command",
    "rng": "Seed/draw folded per inference; draw continues across Stop/resume",
    "pairing_limit": (
        "Same RNG schedule; wall-time inference waits can change pre-intervention physics"
    ),
    "min_lift_m": 0.08, "max_translation_m": 0.01, "max_joint_range_rad": 0.02,
    "min_hold_wall_s": 2, "min_hold_sim_s_exclusive": 1,
    "stop": "Evaluator-triggered HTTP Stop, independent of inference; no speech timing claim",
    "resume": "Clear old action chunk; request fresh camera/proprioception observation",
    "actor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
(args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
(args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
report = {"protocol": protocol, "metadata": metadata, "episodes": []}


def infer(seed, draw):
    encoded = get("/observation", binary=True)
    with np.load(io.BytesIO(encoded), allow_pickle=False) as data:
        obs = dict(data)
    quat = obs["robot0_eef_quat"].copy()
    quat[3] = np.clip(quat[3], -1, 1)
    den = np.sqrt(1 - quat[3] ** 2)
    axis = np.zeros(3) if abs(den) < 1e-8 else quat[:3] * 2 * np.arccos(quat[3]) / den
    prompt = get("/state")["prompt"]
    request = {
        "observation/image": image_tools.convert_to_uint8(image_tools.resize_with_pad(
            np.ascontiguousarray(obs["agentview_image"][::-1, ::-1]), 224, 224)),
        "observation/wrist_image": image_tools.convert_to_uint8(image_tools.resize_with_pad(
            np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1]), 224, 224)),
        "observation/state": np.concatenate((obs["robot0_eef_pos"], axis,
                                              obs["robot0_gripper_qpos"])),
        "prompt": prompt, "experiment_seed": seed, "experiment_draw": draw,
    }
    start = time.monotonic()
    reply = client.infer(request)
    assert reply["experiment_rng"] == {"seed": seed, "draw": draw}
    actions = np.asarray(reply["actions"])
    assert actions.ndim == 2 and actions.shape[1] == 7 and len(actions) >= 5
    assert np.isfinite(actions).all()
    return {"actions": actions[:5].tolist(), "draw": draw,
            "client_ms": (time.monotonic() - start) * 1000,
            "observation_sha256": hashlib.sha256(encoded).hexdigest(),
            "requested_at_wall_s": start}


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as worker:
    for spec in episodes:
        trial = args.output / f"task{spec['task_id']}-seed{spec['seed']}-{spec['variant']}"
        trial.mkdir()
        result = {**spec, "error": None, "trigger_reached": False,
                  "hold_passed": False, "native_success": False,
                  "correction_submitted": False, "fresh_resume_inference": False}
        rows, calls, submissions, held = [], [], [], []
        future, future_epoch, draw, corrected = None, None, 0, False
        try:
            post("/initialize", {"task_id": spec["task_id"]})
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                state, judge = get("/state"), get("/judge")
                rows.append({"wall_s": time.monotonic(), "state": state, "judge": judge})
                if judge and state["physics_ready"]:
                    (trial / "latest.jpg").write_bytes(get("/frame.jpg", binary=True))
                if state["phase"] in ("success", "failed"):
                    result["native_success"] = state["phase"] == "success"
                    result["terminal_state"] = state
                    break
                if (not result["trigger_reached"] and judge
                        and judge["grasp_contacts"]
                        and judge["xyz"][2] - judge["initial_xyz"][2] >= .08):
                    result["trigger_reached"] = True
                    old_epoch = state["epoch"]
                    post("/stop", {})
                    origin = get("/stop-judge")
                    assert origin and get("/state")["phase"] == "paused"
                    held.append(origin)
                    started = time.monotonic()
                    while (time.monotonic() - started < 2
                           or held[-1]["sim_time"] - origin["sim_time"] <= 1):
                        assert time.monotonic() - started < 5, "Physics stalled during hold"
                        held.append(get("/judge"))
                        assert get("/state")["phase"] == "paused"
                        time.sleep(.025)
                    result["hold_wall_s"] = time.monotonic() - started
                    xyz = np.array([s["xyz"] for s in held])
                    joints = np.array([s["joints"] for s in held])
                    result.update(
                        min_hold_lift_m=min(s["xyz"][2] - s["initial_xyz"][2] for s in held),
                        max_hold_translation_m=float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
                        max_hold_joint_range_rad=float(np.max(np.ptp(joints, axis=0))),
                        all_hold_grasp_contacts=all(s["grasp_contacts"] for s in held),
                        hold_sim_s=held[-1]["sim_time"] - origin["sim_time"],
                    )
                    result["hold_passed"] = (
                        result["min_hold_lift_m"] >= .08
                        and result["max_hold_translation_m"] <= .01
                        and result["max_hold_joint_range_rad"] <= .02
                        and result["all_hold_grasp_contacts"]
                    )
                    if future is not None:
                        discarded = future.result(timeout=30)
                        calls.append({**discarded, "discarded_after_stop": True})
                        future = None
                    try:
                        post("/actions", {"epoch": old_epoch, "actions": [[0.] * 7]})
                        raise AssertionError("Stale generation accepted")
                    except urllib.error.HTTPError as caught:
                        assert caught.code == 409
                    post("/resume", {})
                    result["resume_wall_s"] = time.monotonic()
                    result["resume_epoch"] = get("/state")["epoch"]
                    continue
                if future is not None and future.done():
                    call = future.result()
                    calls.append(call)
                    chunk = np.array(call["actions"])
                    if spec["variant"] == "x+3mm" and not corrected:
                        close = np.flatnonzero(chunk[:, 6] > 0)
                        if len(close):
                            index = int(close[0])
                            assert -1 <= chunk[index, 0] + .06 <= 1
                            chunk[index, 0] += .06
                            corrected = True
                            result["correction_submitted"] = True
                    accepted = post("/actions", {"epoch": future_epoch,
                                                  "actions": chunk.tolist()})
                    submissions.append({"draw": call["draw"], "epoch": future_epoch,
                                        "actions": chunk.tolist(), "state": accepted})
                    if future_epoch == result.get("resume_epoch"):
                        assert call["requested_at_wall_s"] >= result["resume_wall_s"]
                        result["fresh_resume_inference"] = True
                    future = None
                elif (future is None and state["phase"] == "running"
                      and state["physics_ready"] and not state["queued_actions"]):
                    future_epoch = state["epoch"]
                    future = worker.submit(infer, spec["seed"], draw)
                    draw += 1
                time.sleep(.015)
            else:
                raise AssertionError("Episode observation deadline")
            if future is not None:
                calls.append({**future.result(timeout=30), "discarded_at_terminal": True})
                future = None
            result["development_passed"] = (
                result["hold_passed"] and result["native_success"]
                and result["fresh_resume_inference"]
            )
        except Exception as caught:
            result["error"] = repr(caught)
            post("/stop", {})
        for filename, data in (("trace.json", rows), ("calls.json", calls),
                               ("submissions.json", submissions), ("hold.json", held),
                               ("result.json", result)):
            (trial / filename).write_text(json.dumps(data, indent=2))
        report["episodes"].append(result)
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(result), flush=True)
        if result["error"]:
            raise SystemExit("Infrastructure failure retained; remaining episodes not attempted")
