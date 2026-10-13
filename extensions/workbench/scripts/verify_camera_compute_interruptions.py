"""Stop real camera/kinematic workers and independently judge resumed journeys."""

import argparse
import hashlib
import json
import threading
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_tasks import CameraTasks
from physical_ai_lab.assistant.perception_scene import camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ik-backend", choices=["legacy", "mink"], default="legacy")
    args = parser.parse_args()
    if args.ik_backend == "mink":
        from mink_robot_adapter import MinkRobot

        from physical_ai_lab.assistant import camera_tasks

        class MinkGuardedRobot(camera_tasks.GuardedRobot, MinkRobot):
            pass

        camera_tasks.SimRobot = MinkRobot
        camera_tasks.GuardedRobot = MinkGuardedRobot
    root = Path(__file__).resolve().parents[1]
    raw = (root / "fixtures/camera_compute_interrupt_protocol.json").read_bytes()
    protocol = json.loads(raw)
    fixture = (root / protocol["known_fixture"]).read_bytes()
    assert hashlib.sha256(fixture).hexdigest() == protocol["known_fixture_sha256"]
    known = next(c for c in json.loads(fixture)["cases"] if c["id"] == protocol["known_case"])
    criteria = protocol["criteria"]
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    cases = [(tool, phase, False) for tool in protocol["tools"] for phase in protocol["phases"]]
    cases += [(known["tool"], phase, True) for phase in protocol["loss_phases"]]
    for tool, phase, loss in cases:
        bench = ToolWorkbench(
            known["seed"] if loss else 42,
            xml=camera_scene_xml(known if loss else {"layout": {}}, alternate_view=True),
        )
        if loss:
            bench.model.vis.headlight.diffuse[:] *= known["light"]
        epoch, stop = [0], threading.Event()
        hub = CameraTasks(bench, lambda: epoch[0], stop.is_set)
        truth, native_tick = bench.observe, bench.tick
        initial = truth()
        maximum, disturbance = initial[tool][2], 0.0

        def measured_tick(*inputs, **options):
            nonlocal maximum, disturbance
            native_tick(*inputs, **options)
            positions = truth()
            maximum = max(maximum, positions[tool][2])
            disturbance = max(
                disturbance,
                max(
                    float(np.linalg.norm(xyz - initial[name]))
                    for name, xyz in positions.items()
                    if name != tool
                ),
            )

        def denied(*unused):
            raise AssertionError("Actor requested privileged tool state")

        bench.tick, bench.observe, bench.tool_support_height = measured_tick, denied, denied
        compute = hub.compute
        triggered, timers = [False], []
        completed = threading.Event()

        def instrumented(work):
            if not triggered[0] and hub.active and hub.active.phase == phase:
                triggered[0] = True
                started = threading.Event()

                def delayed():
                    started.set()
                    time.sleep(protocol["worker_delay_s"])
                    try:
                        return work()  # Real detector/solver, never a synthetic result.
                    finally:
                        completed.set()

                def interrupt():
                    started.wait(timeout=2)
                    time.sleep(protocol["stop_after_worker_start_s"])
                    epoch[0] += 1
                    stop.set()

                timer = threading.Thread(target=interrupt)
                timers.append(timer)
                timer.start()
                return compute(delayed)
            return compute(work)

        hub.compute = instrumented
        controller = hub.task(bench, tool)
        row = {"tool": tool, "phase": phase, "known_loss": loss, "passed": False}
        phases_seen = []
        redirected = False
        try:
            for _ in range(protocol["frame_limit"]):
                more = controller.advance()
                if not phases_seen or phases_seen[-1] != controller.phase:
                    phases_seen.append(controller.phase)
                if not more:
                    raise RuntimeError("Task ended before requested computation was interrupted")
                if stop.is_set():
                    break
                if loss and not redirected and controller.phase == "Moving to target":
                    controller.pause()
                    for _ in range(19):
                        bench.tick()
                    controller.return_to_rack()
                    redirected = True
            else:
                raise RuntimeError("Interruption frame limit exceeded")
            assert triggered[0] and controller.cancelled_generation
            controller.pause()
            joints = controller.robot.read().joints
            position, command = truth()[tool], bench.data.ctrl[7]
            drift = translation = 0.0
            minimum = position[2]
            for _ in range(protocol["hold_frames"]):
                bench.tick()
                drift = max(drift, float(np.max(np.abs(controller.robot.read().joints - joints))))
                actual = truth()[tool]
                translation = max(translation, float(np.linalg.norm(actual - position)))
                minimum = min(minimum, actual[2])
                assert bench.data.ctrl[7] == command
            hold_pass = drift < criteria["joint_drift_rad"]
            if not loss:
                hold_pass &= translation < criteria["held_translation_m"]
                if position[2] >= criteria["held_height_m"]:
                    hold_pass &= minimum >= criteria["held_height_m"]
            assert completed.wait(timeout=2), "Abandoned real worker did not complete"
            row["hold"] = {
                "simulation_s": 32,
                "joint_drift_rad": drift,
                "tool_translation_m": translation,
                "minimum_tool_height_m": float(minimum),
                "gripper_command_retained": True,
                "passed": bool(hold_pass),
            }
            budgets = (
                controller.actor.grip_recovery_attempts,
                controller.actor.correction_attempts,
            )
            stop.clear()
            controller.resume()
            row["resume_outcome"] = asdict(controller.outcome) if controller.outcome else None
            row["budgets_after_resume"] = (
                controller.actor.grip_recovery_attempts,
                controller.actor.correction_attempts,
            )
            for _ in range(protocol["frame_limit"]):
                if not controller.advance():
                    break
            actual = truth()[tool]
            target = initial[tool][:2] if loss else HANDOFF["handoff"]
            distance = float(np.linalg.norm(actual[:2] - target))
            address = bench.model.joint(f"{tool}_joint").dofadr[0]
            speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
            opened = bool(bench.data.qpos[7:9].sum() > 0.07)
            row.update(
                distance_m=distance,
                height_m=float(actual[2]),
                speed_m_s=speed,
                lift_m=float(maximum - initial[tool][2]),
                unrelated_m=disturbance,
                opened=opened,
                budgets_before_resume=budgets,
                budgets_after=(
                    controller.actor.grip_recovery_attempts,
                    controller.actor.correction_attempts,
                ),
                outcome=asdict(controller.outcome) if controller.outcome else None,
                diagnostics=controller.diagnostics(),
            )
            row["passed"] = bool(
                hold_pass
                and distance < criteria["placement_m"]
                and actual[2] < criteria["rest_height_m"]
                and speed < criteria["rest_speed_m_s"]
                and maximum - initial[tool][2] >= criteria["lift_m"]
                and disturbance < criteria["unrelated_translation_m"]
                and opened
                and controller.outcome
                and controller.outcome.status == "success"
                and row["budgets_after_resume"] == budgets
                and controller.actor.grip_recovery_attempts >= budgets[0]
                and controller.actor.correction_attempts >= budgets[1]
            )
        except (AssertionError, RuntimeError, ValueError) as error:
            row["error"] = str(error)
            row["ended_outcome"] = asdict(controller.outcome) if controller.outcome else None
            row["ended_phase"] = controller.phase
            row["ended_diagnostics"] = controller.diagnostics()
        finally:
            for timer in timers:
                timer.join(timeout=3)
            hub.close()
            bench.close()
        rows.append(row)
        row["phases_seen"] = phases_seen
        (args.output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps({k: v for k, v in row.items() if k != "diagnostics"}), flush=True)
    summary = {
        "ik_backend": args.ik_backend,
        "protocol_sha256": hashlib.sha256(raw).hexdigest(),
        "cases": len(rows),
        "passes": sum(row["passed"] for row in rows),
        "passed": all(row["passed"] for row in rows),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
