"""Loopback LIBERO execution boundary. Physics keeps stepping during inference and Stop."""

import argparse
import collections
import io
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--port", type=int, default=8901)
parser.add_argument("--hold-profile", choices=("native", "captured", "joint"), default="joint")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
sys.path.insert(0, str(source / "third_party/libero"))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
sys.path.insert(0, str(source))

import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from PIL import Image  # noqa: E402
from robosuite.controllers.joint_pos import JointPositionController  # noqa: E402


class Runtime:
    def __init__(self):
        self.lock = threading.RLock()
        self.epoch = 0
        self.phase = "idle"
        self.task_id = None
        self.prompt = None
        self.pending_init = None
        self.env = None
        self.obs = None
        self.queue = collections.deque()
        self.grip = -1.0
        self.policy_steps = self.hold_steps = 0
        self.initial_xyz = None
        self.frame = b""
        self.error = None
        self.observation_bytes = None
        self.judge_snapshot = None
        self.inflight_epoch = None
        self.active_steps = 0
        self.goal_override = None
        self.hold_mode = None
        self.original_nullspace = None
        self.joint_hold = None
        self.joint_hold_active = False
        self.hold_diagnostics = None
        self.stop_requested_wall_s = None
        self.stop_judge_snapshot = None
        self.trace = (args.output / "physics.jsonl").open("w", buffering=1)
        self.suite = benchmark.get_benchmark_dict()["libero_spatial"]()

    def state(self):
        return {
            "epoch": self.epoch,
            "phase": self.phase,
            "task_id": self.task_id,
            "prompt": self.prompt,
            "queued_actions": len(self.queue),
            "grip_command": self.grip,
            "policy_steps": self.policy_steps,
            "hold_steps": self.hold_steps,
            "error": self.error,
            "controller": "libero_osc_pose",
            "hardware": False,
            "physics_ready": self.observation_bytes is not None,
            "inflight_epoch": self.inflight_epoch,
            "active_steps": self.active_steps,
            "hold_profile": args.hold_profile,
            "pause_joint_kp": 300 if args.hold_profile == "joint" else None,
            "pause_joint_damping_ratio": 2 if args.hold_profile == "joint" else None,
            "stop_requested_wall_s": self.stop_requested_wall_s,
        }

    def initialize(self, task_id, expected_epoch=None):
        if expected_epoch is not None and expected_epoch != self.epoch:
            raise ValueError("Scene decision discarded after an intervening command")
        if type(task_id) is not int or task_id not in (0, 1, 2):
            raise ValueError("Only frozen supported tasks 0, 1 and 2 are available")
        if self.phase not in ("idle", "success", "failed"):
            raise ValueError("Finish or resume this episode before choosing a new layout")
        self.epoch += 1
        self.queue.clear()
        self.phase = "initializing"
        self.error = None
        self.stop_requested_wall_s = None
        self.task_id = task_id
        self.observation_bytes = None
        self.judge_snapshot = self.stop_judge_snapshot = None
        self.pending_init = (task_id, self.epoch)
        return self.state()

    def stop(self):
        self.stop_requested_wall_s = time.monotonic()
        self.stop_judge_snapshot = self.judge_snapshot
        self.epoch += 1
        self.queue.clear()
        if self.phase in ("initializing", "running", "paused"):
            self.phase = "paused"
        return self.state()

    def resume(self, expected_epoch=None):
        if expected_epoch is not None and expected_epoch != self.epoch:
            raise ValueError("Resume decision discarded after an intervening command")
        if self.phase != "paused" or self.observation_bytes is None:
            raise ValueError("No paused episode to resume")
        self.epoch += 1
        self.queue.clear()
        self.phase = "running"
        return self.state()

    def enqueue(self, epoch, actions):
        data = np.asarray(actions, float)
        if type(epoch) is not int or self.phase != "running" or epoch != self.epoch:
            raise ValueError("Stale or stopped action generation rejected")
        if data.ndim != 2 or data.shape[1] != 7 or not 1 <= len(data) <= 5:
            raise ValueError("Supply one to five explicit LIBERO OSC actions")
        if not np.isfinite(data).all() or self.queue:
            raise ValueError("Non-finite actions or an undrained queue")
        self.queue.extend(a.copy() for a in data)
        return self.state()

    def judge(self):
        # Evaluator-only truth; /observation supplies no object positions.
        if self.env is None:
            return None
        native = self.env.env
        name = "akita_black_bowl_1"
        body = native.obj_body_id[name]
        xyz = native.sim.data.body_xpos[body].copy()
        obj = native.objects_dict[name]
        robot = native.robots[0]
        grasp = native._check_grasp(robot.gripper, obj.contact_geoms)
        return {
            "object": name,
            "xyz": xyz.tolist(),
            "initial_xyz": self.initial_xyz,
            "grasp_contacts": bool(grasp),
            "success": bool(native._check_success()),
            "joints": robot._joint_positions.tolist(),
            "qvel": native.sim.data.qvel[robot._ref_joint_vel_indexes].tolist(),
            "sim_time": float(native.sim.data.time),
            "sampled_wall_s": time.monotonic(),
        }

    def tick(self):
        with self.lock:
            pending, self.pending_init = self.pending_init, None
        if pending is not None:
            task_id, init_epoch = pending
            if self.env is not None:
                self.env.close()
            self.env, self.prompt = _get_libero_env(self.suite.get_task(task_id), 256, 7)
            # Interactive pauses can outlive robosuite's horizon. Keep task
            # success unchanged and enforce the original 220 active-step budget
            # ourselves, counting inference waits but excluding explicit pauses.
            self.env.env.ignore_done = True
            assert self.env.env.robots[0].controller.name == "OSC_POSE"
            self.env.reset()
            self.obs = self.env.set_init_state(self.suite.get_task_init_states(task_id)[0])
            for _ in range(10):
                self.obs, _, _, _ = self.env.step(LIBERO_DUMMY_ACTION)
            self.task_id = task_id
            self.initial_xyz = self.env.env.sim.data.body_xpos[
                self.env.env.obj_body_id["akita_black_bowl_1"]
            ].tolist()
            self.grip = -1.0
            self.policy_steps = self.hold_steps = 0
            self.active_steps = 0
            self.goal_override = None
            self.hold_mode = None
            controller = self.env.env.robots[0].controller
            self.original_nullspace = controller.initial_joint.copy()
            original_set_goal = controller.set_goal
            original_run_controller = controller.run_controller
            self.joint_hold_active = False

            def set_goal(action, set_pos=None, set_ori=None):
                if self.goal_override is not None:
                    set_pos, set_ori = self.goal_override
                return original_set_goal(action, set_pos=set_pos, set_ori=set_ori)

            if args.hold_profile == "captured":
                controller.set_goal = set_goal
            if args.hold_profile == "joint":
                self.joint_hold = JointPositionController(
                    sim=controller.sim,
                    eef_name=controller.eef_name,
                    joint_indexes={
                        "joints": controller.joint_index,
                        "qpos": controller.qpos_index,
                        "qvel": controller.qvel_index,
                    },
                    actuator_range=controller.actuator_limits,
                    kp=300,
                    damping_ratio=2,
                )

                def run_controller():
                    osc_torques = original_run_controller()
                    # Publish proprioception and evaluator truth at the native
                    # control rate, rather than an older rendered-frame tick.
                    # This stays on the sole physics-owning thread.
                    sensor = self.judge()
                    with self.lock:
                        self.judge_snapshot = sensor
                        paused = self.phase == "paused"
                    if paused and not self.joint_hold_active:
                        self.enter_joint_hold()
                    elif not paused:
                        self.joint_hold_active = False
                    return (
                        self.joint_hold.run_controller() if self.joint_hold_active else osc_torques
                    )

                # Both return seven arm torques through the original robot's
                # clipping path. No policy OSC vector is treated as joint angles.
                controller.run_controller = run_controller
            with self.lock:
                if self.epoch == init_epoch and self.phase == "initializing":
                    self.phase = "running"
                else:
                    self.phase = "paused"
        if self.env is None:
            return
        with self.lock:
            mode = (
                "joint_hold"
                if args.hold_profile == "joint" and self.phase == "paused"
                else "osc_hold"
            )
            selected_epoch = self.epoch
            selected_at = time.monotonic()
            selected_phase = self.phase
            if selected_phase == "running":
                self.active_steps += 1
            if self.phase == "running" and self.queue:
                action = self.queue.popleft()
                self.grip = float(action[6])
                self.policy_steps += 1
                mode = "policy"
                self.inflight_epoch = selected_epoch
            else:
                # Neutral OSC displacement preserves grip with real gravity and
                # damping. Never edit object poses, velocities or attachments.
                action = np.array([0.0] * 6 + [self.grip])
                self.hold_steps += 1
                self.inflight_epoch = None
        if args.hold_profile == "captured":
            controller = self.env.env.robots[0].controller
            hold_mode = None if mode == "policy" else selected_phase
            if hold_mode != self.hold_mode:
                controller.update(force=True)
                if hold_mode == "paused":
                    controller.update_initial_joints(self.env.env.robots[0]._joint_positions.copy())
                    self.goal_override = (controller.ee_pos.copy(), controller.ee_ori_mat.copy())
                elif hold_mode is not None:
                    controller.update_initial_joints(self.original_nullspace.copy())
                    self.goal_override = (controller.goal_pos.copy(), controller.goal_ori.copy())
                else:
                    controller.update_initial_joints(self.original_nullspace.copy())
                    self.goal_override = None
                self.hold_mode = hold_mode
        self.obs, _, done, _ = self.env.step(action.tolist())
        with self.lock:
            self.inflight_epoch = None
            if self.phase == "running" and done:
                if not self.env.env._check_success():
                    raise RuntimeError("Simulator done without task success")
                self.phase = "success"
                self.queue.clear()
            if self.phase == "running" and self.active_steps >= 220 and not done:
                self.phase = "failed"
                self.queue.clear()
                self.error = "Original 220 active-step limit reached (inference waits included)"
        pixels = np.ascontiguousarray(self.obs["agentview_image"][::-1, ::-1])
        output = io.BytesIO()
        Image.fromarray(pixels).save(output, format="JPEG")
        observation = io.BytesIO()
        keys = [
            "agentview_image",
            "robot0_eye_in_hand_image",
            "robot0_eef_pos",
            "robot0_eef_quat",
            "robot0_gripper_qpos",
        ]
        np.savez(observation, **{key: self.obs[key] for key in keys})
        judge = self.judge()
        with self.lock:
            self.frame = output.getvalue()
            self.observation_bytes = observation.getvalue()
            self.judge_snapshot = judge
            state = self.state()
        self.trace.write(
            json.dumps(
                {
                    "wall_s": time.monotonic(),
                    "source": mode,
                    "action": action.tolist(),
                    **state,
                    "selected_epoch": selected_epoch,
                    "selected_at_wall_s": selected_at,
                    "judge": judge,
                    "hold_diagnostics": self.hold_diagnostics,
                    "brake_interrupted_inflight_step": self.joint_hold_active
                    and selected_phase != "paused",
                }
            )
            + "\n"
        )

    def enter_joint_hold(self):
        # Invoked inside the native 2 ms torque loop, including an already
        # running env.step. Capture measured robot joints, never object state.
        self.joint_hold.update(force=True)
        velocity = self.joint_hold.joint_vel.copy()
        self.joint_hold.set_goal(np.zeros(7), set_qpos=self.joint_hold.joint_pos.copy())
        self.joint_hold_active = True
        self.hold_diagnostics = {
            "entry_velocity": velocity.tolist(),
            "kd": self.joint_hold.kd.tolist(),
            "goal_joints": self.joint_hold.goal_qpos.tolist(),
            "kp": self.joint_hold.kp.tolist(),
            "damping_ratio": 2,
            "brake_started_wall_s": time.monotonic(),
            "brake_started_sim_time": float(self.env.env.sim.data.time),
            "stop_requested_wall_s": self.stop_requested_wall_s,
        }


runtime = Runtime()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *unused):
        pass

    def reply(self, value, status=200, kind="application/json"):
        data = json.dumps(value).encode() if kind == "application/json" else value
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        with runtime.lock:
            if self.path == "/state":
                return self.reply(runtime.state())
            if self.path == "/judge":
                return self.reply(runtime.judge_snapshot)
            if self.path == "/stop-judge":
                return self.reply(runtime.stop_judge_snapshot)
            if self.path == "/frame.jpg":
                return self.reply(runtime.frame, kind="image/jpeg")
            if self.path == "/observation" and runtime.observation_bytes is not None:
                return self.reply(runtime.observation_bytes, kind="application/octet-stream")
        self.reply({"error": "Unknown or unavailable endpoint"}, 404)

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= 16384:
                raise ValueError("Request size exceeded")
            body = json.loads(self.rfile.read(size) or b"{}")
            with runtime.lock:
                if self.path == "/initialize":
                    result = runtime.initialize(body["task_id"], body.get("expected_epoch"))
                elif self.path == "/stop":
                    result = runtime.stop()
                elif self.path == "/resume":
                    result = runtime.resume(body.get("expected_epoch"))
                elif self.path == "/actions":
                    result = runtime.enqueue(body["epoch"], body["actions"])
                elif self.path == "/release-held-grasp":
                    if runtime.phase != "paused":
                        raise ValueError("Evaluator release probe requires a paused episode")
                    runtime.grip = -1.0
                    result = runtime.state()
                else:
                    raise ValueError("Unknown command")
            self.reply(result)
        except (ValueError, KeyError, TypeError) as caught:
            self.reply({"error": str(caught)}, 409)


server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
print(f"LIBERO physics boundary http://127.0.0.1:{args.port}", flush=True)
try:
    while True:
        started = time.monotonic()
        try:
            runtime.tick()
        except Exception as caught:
            with runtime.lock:
                runtime.phase = "failed"
                runtime.error = repr(caught)
                runtime.queue.clear()
                print(runtime.error, flush=True)
            raise
        time.sleep(max(0, 0.05 - (time.monotonic() - started)))
except KeyboardInterrupt:
    pass
finally:
    server.shutdown()
    if runtime.env is not None:
        runtime.env.close()
    runtime.trace.close()
