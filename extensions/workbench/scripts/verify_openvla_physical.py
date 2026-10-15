"""Frozen six-episode OpenVLA-OFT grasp, Stop, dense hold and fresh-resume evaluation."""

import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--sim-port", type=int, default=8901)
parser.add_argument("--policy-port", type=int, default=8900)
parser.add_argument("--server-log", type=Path, required=True)
parser.add_argument("--validation-state-index", type=int, choices=(5, 6))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
base = "http://127.0.0.1:" + str(args.sim_port)


def get(route, binary=False):
    with urllib.request.urlopen(base + route, timeout=10) as response:
        data = response.read()
    return data if binary else json.loads(data)


def post(route, body):
    request = urllib.request.Request(base + route, json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(request, timeout=10))


def record_frame(trial, frames, pixels, observed_sim_time):
    digest = hashlib.sha256(pixels).hexdigest()
    if frames and digest == frames[-1]["sha256"]:
        return
    name = f"{len(frames):05d}.jpg"
    (trial/"frames"/name).write_bytes(pixels)
    frames.append({"file": name, "wall_s": time.monotonic(), "sha256": digest,
                   "observed_judge_sim_time": observed_sim_time})


policy_url = f"http://127.0.0.1:{args.policy_port}"
with urllib.request.urlopen(policy_url+"/metadata", timeout=10) as response:
    metadata = json.load(response)
assert metadata["device"] == "cuda:0" and metadata["dtype"] == "torch.bfloat16"
assert metadata["warmup_complete"] and metadata["discarded_warmup_actions"] == 8
assert metadata["checkpoint_revision"] == "6d0231af0e48c5985f1ff86908f4674b84bc049b"
frozen_name = ("action-head-validation-protocol.json" if args.validation_state_index is not None
               else "openvla-prospective-protocol.json")
frozen_path = Path(__file__).resolve().parents[1]/"docs"/frozen_name
protocol = json.loads(frozen_path.read_text())
episodes = [{"task_id": task, "repeat": repeat}
            for task in (0, 1, 2) for repeat in (1, 2)]
if args.validation_state_index is not None:
    assert set(metadata["heads"]) == {"original", "step50", "step200"}
    assert set(metadata["warmup_ms_by_head"]) == set(metadata["heads"])
    episodes = [{"task_id": task, "repeat": args.validation_state_index-4,
                 "initial_state_index": args.validation_state_index, "head": head}
                for task in (0, 1, 2) for head in protocol["heads"]]
    protocol["batch_initial_state_index"] = args.validation_state_index
protocol.update(episodes=episodes,
                server_trace_offset=len(args.server_log.read_text().splitlines()),
                transport="Eight-action prediction submitted as bounded5+3 packets; clear on Stop",
                frozen_protocol_sha256=hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
                actor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                runtime_sha256=hashlib.sha256(Path(__file__).with_name(
                    "libero_runtime.py").read_bytes()).hexdigest())
(args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
(args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
for name in ("libero_runtime.py",):
    (args.output / name).write_bytes(Path(__file__).with_name(name).read_bytes())
report = {"protocol": protocol, "metadata": metadata, "episodes": []}


def infer(draw, head_name="original"):
    before = get("/state")
    assert before["physics_ready"]
    assert before["native_init_epoch"] == before["scene_request_epoch"]
    encoded = get("/observation", binary=True)
    after = get("/state")
    assert after["native_init_epoch"] == before["native_init_epoch"]
    assert after["scene_request_epoch"] == before["scene_request_epoch"]
    request = urllib.request.Request(policy_url+"/infer", encoded,
                                     {"Content-Type": "application/octet-stream",
                                      "X-Task-Prompt": after["prompt"],
                                      "X-Action-Head": head_name,
                                      "X-Request-Id": str(draw)})
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=30) as response:
        reply = json.load(response)
    assert reply["request_id"] == draw
    assert reply["observation_sha256"] == hashlib.sha256(encoded).hexdigest()
    if args.validation_state_index is not None:
        assert reply["head"] == head_name
        assert reply["head_sha256"] == metadata["heads"][head_name]["sha256"]
    actions = np.asarray(reply["actions"])
    assert actions.shape == (8, 7)
    assert np.isfinite(actions).all()
    return {"actions": actions.tolist(), "draw": draw, "server_ms": reply["server_ms"],
            "head": head_name, "head_sha256": reply.get("head_sha256"),
            "client_ms": (time.monotonic() - start) * 1000,
            "observation_sha256": hashlib.sha256(encoded).hexdigest(),
            "requested_at_wall_s": start}


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as worker:
    for spec in episodes:
        trial = args.output / f"task{spec['task_id']}-repeat{spec['repeat']}"
        if args.validation_state_index is not None:
            trial = args.output/f"task{spec['task_id']}-repeat{spec['repeat']}-{spec['head']}"
        trial.mkdir()
        (trial/"frames").mkdir()
        result = {**spec, "error": None, "trigger_reached": False,
                  "hold_passed": False, "native_success": False,
                  "fresh_resume_inference": False}
        rows, calls, submissions, held, frames = [], [], [], [], []
        future, future_epoch, draw = None, None, 0
        pending, pending_call, pending_epoch, part = [], None, None, 0
        try:
            initialized = post("/initialize", {"task_id": spec["task_id"]})
            assert initialized["motion_profile"] == "baseline"
            assert initialized["dense_hold_capture"]
            assert not initialized["carry_governor_experiment"]
            if args.validation_state_index is not None:
                assert initialized["initial_state_index"] == spec["initial_state_index"]
                assert initialized["require_released_placement"]
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                state, judge = get("/state"), get("/judge")
                rows.append({"wall_s": time.monotonic(), "state": state, "judge": judge})
                if judge and state["physics_ready"]:
                    pixels = get("/frame.jpg", binary=True)
                    (trial / "latest.jpg").write_bytes(pixels)
                    if args.validation_state_index is not None:
                        record_frame(trial, frames, pixels, judge["sim_time"])
                if state["phase"] in ("success", "failed"):
                    result["discarded_local_at_terminal"] = len(pending)
                    result["native_success"] = state["phase"] == "success"
                    result["terminal_state"] = state
                    if args.validation_state_index is not None:
                        release = get("/released-placement")
                        result["released_placement_passed"] = bool(
                            state["phase"] == "success" and release is not None)
                        (trial/"released-placement.json").write_text(json.dumps(release, indent=2))
                    break
                if (not result["trigger_reached"] and judge and state["phase"] == "running"
                        and state["physics_ready"]
                        and judge["native_init_epoch"] == state["scene_request_epoch"]
                        and judge["grasp_contacts"]
                        and judge["xyz"][2] - judge["initial_xyz"][2] >= .08):
                    result["trigger_reached"] = True
                    old_epoch = state["epoch"]
                    scene_epoch = state["scene_request_epoch"]
                    post("/stop", {})
                    result["discarded_local_after_stop"] = len(pending)
                    pending.clear()
                    origin = get("/stop-judge")
                    assert origin and get("/state")["phase"] == "paused"
                    held.append(origin)
                    started = time.monotonic()
                    while (time.monotonic() - started < 2
                           or held[-1]["sim_time"] - origin["sim_time"] <= 1):
                        assert time.monotonic() - started < 5, "Physics stalled during hold"
                        held.append(get("/judge"))
                        assert get("/state")["phase"] == "paused"
                        if args.validation_state_index is not None:
                            record_frame(trial, frames, get("/frame.jpg", binary=True),
                                         held[-1]["sim_time"])
                        time.sleep(.025)
                    result["hold_wall_s"] = time.monotonic() - started
                    dense = [s for s in get("/dense-hold")
                             if s["native_init_epoch"] == scene_epoch
                             and origin["sim_time"]-1e-10 <= s["sim_time"]
                             <= held[-1]["sim_time"]+1e-10]
                    assert len(dense) > 400, "Incomplete native callback coverage"
                    measured = dense+held
                    (trial / "dense-hold.json").write_text(json.dumps(dense, indent=2))
                    xyz = np.array([s["xyz"] for s in measured])
                    joints = np.array([s["joints"] for s in measured])
                    result.update(
                        min_hold_lift_m=min(s["xyz"][2]-s["initial_xyz"][2] for s in measured),
                        max_hold_translation_m=float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
                        max_hold_joint_range_rad=float(np.max(np.ptp(joints, axis=0))),
                        all_hold_grasp_contacts=all(s["grasp_contacts"] for s in measured),
                        native_hold_samples=len(dense),
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
                    try:
                        post("/actions", {"epoch": old_epoch, "actions": [[0.]*7]})
                        raise AssertionError("Stale generation accepted after resume")
                    except urllib.error.HTTPError as caught:
                        assert caught.code == 409
                    result["stale_after_resume_rejected"] = True
                    continue
                if future is not None and future.done():
                    call = future.result()
                    calls.append(call)
                    pending = call["actions"].copy()
                    pending_call, pending_epoch = call, future_epoch
                    part = 0
                    future = None
                elif pending and state["phase"] == "running" and not state["queued_actions"]:
                    chunk, pending = pending[:5], pending[5:]
                    accepted = post("/actions", {"epoch": pending_epoch, "actions": chunk})
                    submissions.append({"draw": pending_call["draw"], "epoch": pending_epoch,
                                        "part": part, "actions": chunk, "state": accepted})
                    part += 1
                    if pending_epoch == result.get("resume_epoch"):
                        assert pending_call["requested_at_wall_s"] >= result["resume_wall_s"]
                        result["fresh_resume_inference"] = True
                elif (future is None and state["phase"] == "running"
                      and not pending and state["physics_ready"] and not state["queued_actions"]):
                    future_epoch = state["epoch"]
                    future = worker.submit(infer, draw, spec.get("head", "original"))
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
                               ("frames.json", frames),
                               ("result.json", result)):
            (trial / filename).write_text(json.dumps(data, indent=2))
        report["episodes"].append(result)
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(result), flush=True)
        if result["error"]:
            report["not_run"] = episodes[len(report["episodes"]):]
            (args.output/"report.json").write_text(json.dumps(report, indent=2))
            raise SystemExit("Infrastructure failure retained; remaining episodes not attempted")
