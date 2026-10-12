# From simulated assistant to a physical workbench arm

Keep the working conversation, task manager, interruption and outcome reporting.
Reuse an established robot driver and an adapted pretrained policy for the chosen
arm. Hardware selection is deferred; this is the preparation plan, not an order
or permission to connect or move a robot.

## What our current simulation actually represents

The current scene is a Panda with approximate primitive tools. A read-only
inventory compiles its MuJoCo model and independently checks catalog bounds
against the compiled collision geometry. It does not step the simulator, render,
connect serial devices or touch real hardware. Evidence is in
`hardware-adaptation-evidence.json`.

| Simulated tool | Authored mass | Overall bounds, X × Y × Z | Grip block |
|---|---:|---:|---:|
| Screwdriver | 76 g | 44 × 202 × 44 mm | 44 × 56 × 44 mm |
| Wrench | 89 g | 64 × 182 × 44 mm | 44 × 56 × 44 mm |
| Hammer | 61 g | 90 × 191 × 44 mm | 44 × 56 × 44 mm |

These are synthetic objects, not measurements of the user's tools. In particular,
the simulated hammer is lighter than the simulated screwdriver. Its successful
transport cannot establish capacity for a real hammer. The simulated gripper also
uses doubled positional-servo stiffness, a setting that cannot be transferred as
a physical grip-force calibration.

Rack centers are 45–48.8 cm from the model base origin in the table plane. The
handoff center is 66.0 cm away, with a 17 × 25 cm mat. These are layout dimensions,
not a measured reachable workspace for a smaller arm. Rebuild the rack and handoff
layout around the chosen robot's kinematics; do not copy Panda coordinates into
an SO-101 controller.

Reproduce the inventory from the lab or exported workbench extension:

```sh
uv run --locked python scripts/inspect_hardware_requirements.py \
  --output runs/hardware-inventory-new.json
```

## Hardware decision based on the job

SO-101 is a candidate for learning and lightweight, constrained tabletop handling.
LeRobot already supplies its follower driver, calibration and demonstration
workflows, and Dum-E already wraps that driver. Reuse this work rather than build
a motor protocol. Its suitability for the intended tools is still unknown.
[LeRobot SO-101](https://huggingface.co/docs/lerobot/so101)

Evaluate the candidate with a concrete tool/layout sheet before a purchase:

| Requirement | Measurement or evidence needed | Current status |
|---|---|---|
| Load at operating reach | Actual tool mass, center of mass, grasp location; include wrist camera and gripper additions | Unmeasured |
| Grasp compatibility | Handle cross-section, available opening, finger contact, surface/friction and observed slip | Synthetic block only |
| Reach and useful orientation | Candidate model reaches every pickup, carry and release pose with the tool attached | Panda scene only |
| Mounting | Stable base, actual tabletop dimensions, clear carry path and accessible pickup tray | No physical station |
| Sensing | Supported cameras, usable views of rack/gripper/tray and calibrated frames | Simulated cameras only |
| Control and interruption | Documented units, limits, feedback, behavior under Stop/link loss and supported driver | Driver exists; hardware untested |
| Demonstrations | Compatible teleoperation method and repeatable recordings for task-specific adaptation | No hardware dataset |

Compare another arm if SO-101 cannot satisfy the measured job. Do not substitute
smaller tools and then claim it handles the original tool set. No payload, reach,
price or force capability is assumed from a name or a marketing limit. A mobile
base can be reconsidered later; the current job is a fixed workbench single arm.

## Adapter boundary: retain the task, replace the embodiment

There are useful boundaries already, but no hardware-compatible adapter has been
demonstrated. `SimRobot` exposes robot readings, motion and hold separately from
the rendered camera port. The Dum-E SO-101 wrapper delegates to LeRobot. Keep the
task lifecycle above these boundaries and make each action representation explicit.

| Interface | Current implementation | Hardware adaptation |
|---|---|---|
| Robot state | Seven Panda joints in radians, TCP in meters, rotation matrix, gap in meters, simulation timestamp | Named calibrated joints; measured/derived pose and gap; monotonic capture time; unsupported feedback explicitly absent |
| Motion | Panda joint-position commands; LIBERO policy uses seven OSC delta/gripper inputs | Chosen robot's supported controller and trained action schema; reject mismatched embodiment/units |
| SO-101 policy state | Upstream wrapper uses five named arm positions plus `gripper.pos`, defaulting to `use_degrees=True` | Verify the installed driver's normalization, especially the gripper, and checkpoint metadata; do not copy six/seven-value arrays by length |
| Camera | RGB-D with simulated calibration and MuJoCo camera-axis convention | Calibrated real sensor frames, depth units if available, timestamp and camera-axis conversion |
| Task outcome | Simulator truth in independent judges; experimental actor says `released_unverified` | Observed grasp/lift/release/resting pose; controller acknowledgment or a model reply is not success |
| Stop | Local task generation invalidation, hold, preserved grip; isolated policy worker cancellation | Robot-side execution cancellation and measured settling independent of network/model completion |

A five-joint arm cannot generally realize every position and orientation of the
seven-joint Panda. Match the station and demonstrated grasp orientations to the
new embodiment. Reuse robot-specific policies or maintained planning software;
do not transplant our custom Panda IK or assume a LIBERO policy controls SO-101.

The existing SO-101 convenience `connect()` requests calibration and applies a
gain preset; its reset/release helpers send fixed poses. They are not read-only
hardware probes or tested workbench skills. Review those side effects before
using them. Commission through explicit LeRobot calibration/driver steps after
hardware authorization, rather than invoking those helpers implicitly.

## Calibration and sensing

After authorization and selection, save a versioned robot/station record: motor
identities and signs, calibrated joint ranges and units, model geometry, base and
TCP transforms, measured gripper opening curve, camera intrinsics/extrinsics,
capture timestamps, and tool geometry/mass. Compare forward-kinematic poses with
independent observations at multiple poses; record residuals and their uncertainty.

The current primitive detector assumes axial depth and known colored 44 × 56 mm
faces. Two ordinary RGB cameras do not supply that depth contract. Either use a
policy adapted to its actual RGB observations, or choose a calibrated depth/pose
method. Detect actual tool identity and uncertainty; never fill a missing view
with a nominal rack position. Wrist and fixed views are useful candidates, but
their mounting and visible coverage must be evaluated in the real station.
[LeRobot cameras](https://huggingface.co/docs/lerobot/cameras)

Simulation timestamps cannot detect a real sensor/network stall. The existing
250 ms freshness gate is in simulation time. Hardware needs wall-clock capture
age, command deadlines and verified clock handling. Calibrate limits from the
selected controller and station before choosing motion speed or grip effort;
retain task-generation checks immediately before execution.

## Progressive adaptation and evidence

1. **Matched pretrained baseline.** Run π0.5-LIBERO in its supported Linux
   simulator first. Record exact checkpoint/runtime, independent task success,
   replay videos, and cold/warm timings. Workstation access is pending. This
   validates reuse, not screwdriver handling or SO-101 transfer.
2. **Embodiment and station simulation.** Use the selected arm's existing model
   and a measured tool/layout catalog. Verify reachable poses and grip geometry,
   then adapt a compatible policy with demonstrations. Keep the old scene and
   frozen fixtures as historical comparisons, not mislabeled hardware twins.
3. **Offline hardware observations, after authorization.** Capture calibration
   and teleoperated demonstrations locally. Replay observations through perception
   and policy without sending actions. Measure action validity, uncertainty and
   timing; split by complete episodes/layouts before tuning. Fine-tuning reuses
   pretrained capabilities; it is not training a foundation model from scratch.
4. **Supervised constrained tray delivery, after authorization.** Start with a
   characterized object and operating envelope, then test the intended tools.
   Measure grip retention, placement, return, task changes and physical Stop
   settling. Include stale camera, disconnected policy and delayed-reply trials.
   Characterize hold/power-loss behavior; stopping software and cutting power
   are different operations. A successful small pilot is not general readiness.
5. **Expanded tools and interaction.** Collect recovery demonstrations and test
   held-out layouts, clutter and occlusion. Establish real-task tolerances before
   promotion, retain failure cases, and compare the reused policy with the existing
   baseline. Keep decorative movements out of manipulation and paused grasps.

The tray remains the first physical pickup location. Direct hand-to-human delivery
is a later, separately validated hardware interaction requiring measured recipient
position and transfer/release behavior. The current green mat does not demonstrate it.

Preserve the existing simulation judges: 35 mm placement, 4 mm unrelated-tool
body-center displacement, 80 mm lift, 40 mm resting-height limit, 30 mm/s resting
speed and 95% full-journey success in the frozen release fixture. They do not
measure all tipping, rotation or contact risks. Hardware evaluation must also
measure those effects; do not silently reinterpret simulation limits as certified
hardware limits or loosen them to make a policy pass.

## Readiness today

The plan and simulated inventory are prepared. No robot is selected, purchased,
connected, calibrated or moved. No real tools/cameras are measured. The generic
adapter, compatible tool policy and hardware limits remain unverified. The full
assistant goal is incomplete; the immediate pretrained-policy experiment needs
access to the existing RTX workstation and a verified compatible Linux runtime.
