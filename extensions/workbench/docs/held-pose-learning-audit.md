# D2e: held geometry and future release learning

**Historical October 11 experiment.** Its two rejected held-view fits, failed
model gate and training-exposure finding remain evidence. Subsequent PC camera
cohorts are documented in [camera-scene-pc.md](camera-scene-pc.md); the old 24
reserved layouts have since been evaluated and are not future unseen tests.
The prepared training-only curriculum has now been collected and its remaining
bounded fit rejected on the PC; see [release-curriculum-pc.md](release-curriculum-pc.md).
The remaining fit budget is zero. Statements below describe the earlier stage.

Experimental, October 11, 2026. Public voice assistant and enabled controllers
remain unchanged. No hardware or camera permissions were added. Full goal active.

## Measured problem

The known validation-016 wrench redirect reproduces the previous **36.424 mm**
placement error exactly. A synchronized diagnostic records camera frames and
robot telemetry; physics poses are separate evaluation labels, never actor inputs.
Before descent, rigid held-center error reaches **15.632 mm** and orientation
error **0.232 rad**. Near release, center error is **33.564 mm** with the jaws
still roughly 43.49 mm apart. A closed gap cannot establish the tool's pose.
Errors after release are not interpreted as held-pose estimates.

Initial diagnostic-001 mixed transition timestamps and compared the final state
with the un-settled layout. It is retained but excluded from camera accuracy and
placement claims. Corrected diagnostic-002 uses synchronized frames and settled
initial positions. Optional-side-camera diagnostic reproduces the same physics.

## Camera hypotheses rejected

Two opt-in fits use only RGB-D, calibration, known handle appearance/dimensions
and measured TCP. The first extends the complete-face detector to airborne
handles. The second fits robust upward-facing depth planes near the gripper.
Both withhold **all 12 airborne frames** from the paired front/side views of
this one validation scene. Parts of the handle are visible (independently labeled
331–1101 pixels), but neither method supports a pose with the unchanged 0.8
geometric fit gate. No measurements are inserted into control and no invisible
edges or truth poses are substituted.

Independent synthetic full-face specifications pass for all three tools, within
1.5 mm; clipped/far/invalid-prior cases withhold. These tests establish units and
refusal behavior, not capability under actual jaw occlusion. Both methods remain
experimental, and neither is a general six-dimensional tracker.

## Counterfactual release evidence

Nine physical release branches from the failing held state reproduce normal and
repeated zero-action integration states with exactly zero discrepancy. A +20 mm
X action reduces future placement error to about **18.2 mm**, versus **36.5 mm**
for zero action, relative to its camera-derived destination. The
independent journey judge uses the settled initial rack position instead. This
is measured counterfactual evidence for one state, not an
accepted live policy or a hard-coded correction. Snapshot resets are confined to
the offline collector.

The recovery-profile dataset contains **1314 outcomes**: 1044 from 116 release
states in 70/72 training scenes, and 270 from 30 states across all 18 validation
scenes. Rejected trajectories remain recorded. All 146 normal/repeated zero-state
checks match exactly. The 24 reserved test layouts remain unopened. Scene splits
and nine ±20 mm action choices retain the original frozen fixture hash.

Outcome label version 2 strengthens added-neighbor displacement to the maximum
sampled every 32 ms during release, using the same 4 mm criterion. The legacy
collector mode retains its final-displacement label. This is body-center
translation, not tool-tip/rotation/sub-frame collision detection.

## First fit and why it is rejected

The existing 76 camera/history/robot/action features, three 9413-parameter members,
fixed seeds and 300 epochs are unchanged. Training-only heading dropout uses the
previous frozen protocol. CPU training takes 3.330 seconds. Validation results:

| Predictor | Future XY RMSE | Future XY p95 |
|---|---:|---:|
| Rigid translation baseline | 14.001 mm | — |
| Per-tool mean | 9.277 mm | 16.136 mm |
| Linear | 22.688 mm | 35.131 mm |
| Neural ensemble | 6.568 mm | 11.109 mm |

All 270 neural rows are covered; batch-of-nine inference median/p95 is
0.075/0.084 ms. The **11.109 mm p95 fails the unchanged 10 mm offline gate**.
No predictor is selected, and no full-loop learned-policy claim is made.

Critically, the training trajectories contain **zero deliberately reoriented
release states**, while validation contains three. Merely collecting the default
recovery policy did not supply the needed experience. Recipe metadata therefore
keeps this model restricted: it cannot authorize deliberately reoriented release.
The old v2 artifact also remains restricted and unchanged. A future model needs
both explicit training exposure and independent physical validation; metadata
alone does not prove it works.

The rejected checkpoint is retained as
`src/physical_ai_lab/assistant/assets/learned/release-outcome-v3-rejected.npz`.
The reproducible dataset and manifest are under `research/release-recovery-001`.
No model is auto-loaded. All force limits, physics and success gates are preserved.

## Reproduce and next action

In the lab Python environment (training requires Torch):

```sh
uv run --locked python scripts/diagnose_held_pose.py runs/held-diagnostic-new --alternate-view
uv run --locked python scripts/probe_held_perception.py runs/held-diagnostic-new runs/held-optics-new
uv run --locked python scripts/collect_release_data.py runs/recovery-data-new --recovery-profile
uv run --locked python scripts/train_release_model.py research/release-recovery-001 \
  runs/recovery-fit-new --sensor-dropout fixtures/release_sensor_dropout.json
```

`fixtures/release_reorientation_protocol.json` freezes the next training-only
orientation curriculum before collecting it. Its implementation and collection
remain the next action; no curriculum trajectories are claimed here. Keep
validation/test scenes untouched, retain refused motions, then allow one remaining
bounded fit before replanning. Require full-journey validation before opening the
24 test scenes or enabling camera operation in the public app.

All-phase camera Stop/resume/replan, public camera operation, useful learned
full-loop gains, cold/audible/noise/live responsiveness, hardware adaptation and
human live demonstration remain unfinished. See the evidence JSON and figure.

Verification: 180 lab tests and 161 independent exported-fork tests pass;
Ruff/format pass for 98 lab and 74 fork Python files. All 46 pinned upstream
source hashes match. Public app observed Ready with voice enabled and microphone
idle; no public UI actions or motions were performed this slice.
