# Opt-in camera workbench interface on the PC

October 13, 2026. Baseline dc708dc has the camera candidate and interrupted
grip-recovery checks, but the public application still routes motion from
simulator object state. Hypothesis: an adapter can reuse the existing Dum-E
task/MCP interface while using camera observations for motion and task context
for dialogue, preserving the original independent physical judge and Stop.

Later repairs and the current candidate are documented in
[live-camera-recovery-pc.md](live-camera-recovery-pc.md). The measurements below
describe d975557 and retain its continued-session failure.

Launch from the repository root:

```powershell
powershell.exe -NoProfile -File .\extensions\workbench\scripts\launch_windows.ps1 -CameraTools
```

Open http://127.0.0.1:8886. The camera simulator/MCP use 8885/8802; the existing
main assistant remains on 8876/8875/8801. Listening starts off. The ordinary
launcher defaults remain unchanged. Port/profile checks reject incompatible
reuse. No pretrained policy or Odyssey endpoint is connected by this switch.

The actor receives calibrated RGB-D frames and robot readings. Initial rack
context comes from camera detections; absent rack context refuses a request.
Both language-model request paths omit simulator coordinates. Inventory reports
camera-confirmed initial racks, unknown current locations, or verified previous
task delivery. Simulator object state is reserved for display/logging and the
separate outcome evaluator, which checks 35mm placement, 80mm lift, rest height
and speed, open fingers and less than 4mm unrelated-object disturbance.

Detection runs on a CPU worker while the native owner thread advances physics
under the original gravity hold. The original camera freshness gate remains.
Cancellation checks the request epoch before physical commands and while waiting
for detection. A cancelled observation is discarded. If cancellation closes a
held motion sequence during camera processing, resume explicitly refuses and
retains the paused context for a fresh destination plan; it does not claim to
continue a closed generator. Ordinary Stop/resume during transport passes.

Measured evidence:

- Default-scene direct pickup and physical return: all three tools, 6/6 legs.
  Placement errors 7.5–17.2mm, lifts 201–228mm. These accelerated native calls
  are physical checks, not wall-clock interaction latency or varied-layout tests.
- Two interface runs: screwdriver delivery with conversation during transport,
  Stop/resume, change to wrench with verified screwdriver return first, then
  contextual wrench return. All four physical placements per run passed.
  Final-source errors: 7.49, 9.69, 10.60 and 15.96mm.
- Final-source HTTP request to observed stopped state: 53.25ms; earlier 54.11ms.
  One observation per run, no percentile or acoustic latency claim. Gripper
  command remained closed. Conversation response HTTP times: 37.70/41.87ms.
- Final-source completion clocks: 8.13s from resume, 35.78s for the two-leg tool
  change, 18.33s for return. These clocks exclude capture/ASR/audible onset and
  do not constitute the full responsiveness benchmark.
- A third run using the reusable script in the same continued session failed
  during the resumed screwdriver carry: "Grip changed during motion; queued
  carry cancelled". The tool fell naturally onto the table. Later change/return
  requests were not executed. Stop observation took 97.31ms in this failed run.
  It began after previously returned tools, rather than an episode reset. Actual
  final screwdriver pose was [0.45647, -0.27834, 0.02166]m; peak lift 187.17mm.
  This exposes unresolved repeatability across returned poses. The cause is not
  established; concurrent tests also changed host load. Preserve both factors
  as confounds, without claiming either caused the loss or changing thresholds.
- Actor truth-denial tests cover all six default-scene legs. Negative tests cover
  late-command rejection, continued physics during detector work, cancelled
  results, missing-rack refusal and retained context after refused resume.
- Final-source lint and all 302 regressions pass; all 46 protected upstream
  hashes match. Passing these tests does not override the continued-session failure.

Reproduce typed interface checks on an idle, initially stocked camera simulator:

```bash
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_live_camera_interface.py runs/new-camera-interface
```

The directory must be new. This script sends simulation requests without
recording microphone audio and reports failed journeys instead of continuing
with a success summary. Its first actual run failed as described above. Raw evidence remains local under
`runs/camera-live-adapter-001` and `runs/dume-52693277`; the adjacent evidence JSON
records summaries and identities. Earlier prospective 53/54 camera evidence
belongs to its frozen offline controller. These few interface runs do not
establish a new prospective full-journey rate or unseen grasp-loss recovery.

The user independently reported “it worked.” for the main assistant's live
microphone screwdriver request. The observed main task succeeded at 9.65mm
placement error; its application completion clock was 16.58s. This confirms one
user-controlled recognition/delivery/audible-reply journey on the main assistant.
It supplies no measured acoustic latency, echo assessment or camera-mode human
qualification.

Rollback: omit `-CameraTools` and use the unchanged main profile. This optional
adapter preserves tool_contacts_v2, geometry, gravity hold and existing success
limits. No fits, checkpoints, hardware, paid requests or project-data uploads.
Next: instrument and investigate the resumed carry failure across returned
poses, then measured saved-audio camera journeys, interruption during real
detection, broader complete live layouts and a user-controlled demonstration.
The sustained goal remains active.
