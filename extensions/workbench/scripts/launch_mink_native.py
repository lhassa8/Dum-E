"""Launch the tested IK backend in a separate, frozen camera workbench process."""

import json

from mink_robot_adapter import MinkRobot

from physical_ai_lab.assistant import camera_tasks


class MinkGuardedRobot(camera_tasks.GuardedRobot, MinkRobot):
    """Original cancellation/physics boundary with the maintained IK solver."""


camera_tasks.SimRobot = MinkRobot
camera_tasks.GuardedRobot = MinkGuardedRobot
OriginalCameraTasks = camera_tasks.CameraTasks


class MeasuredMinkTasks(OriginalCameraTasks):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.measured_tasks = []

    def task(self, *args, **kwargs):
        task = super().task(*args, **kwargs)
        assert isinstance(task.robot, MinkGuardedRobot)
        self.measured_tasks.append(task)
        return task

    def close(self):
        super().close()
        print(
            json.dumps(
                {
                    "motion_backend": "mink",
                    "tasks": [
                        {
                            "object": task.object,
                            "destination": task.destination,
                            "outcome": task.outcome.status if task.outcome else None,
                            "mink_pose_solves": sum(
                                event["kind"] == "mink_pose_solve" for event in task.robot.ik_events
                            ),
                        }
                        for task in self.measured_tasks
                    ],
                }
            ),
            flush=True,
        )


camera_tasks.CameraTasks = MeasuredMinkTasks
print("Experimental Mink IK; original gravity hold and camera/task judges retained.", flush=True)

if __name__ == "__main__":
    from physical_ai_lab.assistant.app import main

    main()
