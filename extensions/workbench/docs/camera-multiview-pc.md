# PC camera experiment: target retry does not establish scene coverage

2026-10-12, baseline `03981be`. The camera actor is still experimental and is
**not promoted** to the public workbench. The new prospective cohort passes
**51/54 complete journeys (94.44%)**, below the unchanged 95% observed gate.
An independent audit reconstructs all 54 verdicts from recorded measurements.
The Wilson 95% interval is 84.89–98.09%; this sample does not establish a
population success probability of 95%.

## Baseline and bounded change

On local WSL2 Python 3.12.3 / MuJoCo 3.15.0 / NumPy 2.5.4, the existing optional
camera profile reproduces **18/18 validation journeys** and **6/6 long-held
continuations**. The original layout fixture remains byte-identical to its
canonical SHA256 `7fda988b669f9ccd79e73ca469c499126e6fe5939ce351f20f4807fc47108197`.
Only proven Windows CRLF conversion was restored; no case was changed.
The long-hold hammer minimum remains 130.089 mm against 130 mm, a narrow margin.

Hypothesis: a target rejected by the primary view could qualify through one
fresh, calibrated side view. The candidate adds opt-in `alternate_view` to
CameraDelivery. It retries once after a primary observation refusal, validates
the entire selected target observation against the original 0.8 fit/freshness/
supported-volume gates, and records both attempts plus total observation time.
There is no nominal-position fallback. The default actor does not enable it.
Rollback is simply leaving the flag off; public workbench behavior is unchanged.
No solver, motion recipe, physics, friction, force limit or learned weight changed.

Tests establish an actual rendered side-view delivery after an unusable primary
depth frame with privileged object APIs denied; two unusable views refuse
without advancing physics; absent alternate calibration also refuses. The
failure path retains the existing gravity hold. An initial test incorrectly
expected nominal HOME control targets to remain unchanged during refusal; its
baseline was corrected to the existing gravity hold, while exact joint poses,
gripper command and simulated time remain checked.

The candidate retains **18/18 validation journeys**. The full-journey judge was
also strengthened: first and return legs must finish release/withdrawal and
show independently measured open fingers, in addition to >=80 mm lift, <35 mm
placement error, resting height <40 mm, speed <30 mm/s and unrelated-tool center
disturbance <4 mm. No threshold was widened. Short pause checks remain the
existing 0.608 simulated seconds / 0.03 rad; the separate six-case 32-second
protocol retains its stricter 0.02 rad / 10 mm / 130 mm gates. None is a live
spoken Stop or wall-clock holding test.

## Prospective cohort and result

Sources, judge, protocol, locked dependencies and runtime were frozen before
generating new coordinates. Text hashes normalize Windows CRLF to LF;
46 protected upstream assets are independently checked byte-for-byte.
The first source snapshot was superseded before any prospective cases were
generated to finish source checks. `frozen-002.json` is the actual evaluation
manifest, preserved in curated evidence.

The declared recipe uses only rounded bounds and the three-lane structure of
the existing **training** cohort: X 0.405–0.475 m; Y lanes -0.22/0/0.22 m with
±20 mm jitter; full planar yaw; lighting 0.8–1.2. Seed 2026101301 generates 54
cases, six in every tool/journey combination, without coordinate filtering or
resampling. Each failed case remains in the denominator. The generated fixture
SHA256 is `76b98a4134055633edf0c0d02dff157af790cd8f193a61492f64897aed603b6e`.

| Evidence | Result |
| --- | --- |
| First-leg lift and resting placement | 53/54 |
| Complete delivery/resume/redirect plus required return | **51/54 — FAIL** |
| Fresh-camera return attempts | 36 |
| Selected alternate target observations | **0** |
| Independent verdict reconstruction | 54/54 agree |
| Workbench regressions | 254 pass |

No alternate target observation was selected, so this cohort establishes no
coverage benefit from the retry. Comparing its 94.44% with the old 22/24 is not
a causal improvement estimate: cohorts differ, and all three failures remain.

- **pc-reserved-000 and 027, screwdriver returns:** initial delivery/resting
  placement passed. Both returns stopped because a neighboring wrench appeared
  ambiguous. The target itself had qualified; target-only retry did not address
  the scene needed to plan placement. The screwdriver remained about 216 mm high,
  261/276 mm from its rack, with fingers closed. Neither return was completed.
- **pc-reserved-052, wrench redirect:** the hold passed, then the encoder grip
  indication disappeared. At failure, XY distance was 31.43 mm but height was
  255.78 mm and speed 0.978 m/s. Nearby XY alone cannot establish placement or
  successful return. The actor held the arm and reported failure.

All data is simulated known-primitive RGB-D. Color/geometry priors, inferred held
pose, bounded stationary-neighbor prediction and 32 ms body-center sampling
remain limitations. General recognition, sub-frame collisions, tip/rotation
safety, all-phase recovery and human acoustic timing are not established.

## Reproduce and next experiment

From the extension root in the prepared WSL environment:

```bash
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/fresh-camera-freeze.json --freeze
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/fresh-camera-cases.json \
  --manifest runs/fresh-camera-freeze.json
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_delivery.py runs/fresh-camera-results \
  --fixture runs/fresh-camera-cases.json --split heldout --recover-ik --verify-motion \
  --release-fallback --linear-lifts --center-grasp --safe-handoff --alternate-view \
  --return-after-delivery
.venv-linux/bin/python scripts/audit_camera_journeys.py runs/fresh-camera-results/results.json \
  runs/fresh-camera-results/audit.json --protocol fixtures/camera_multiview_protocol.json
```

This reproduces the now-evaluated cohort; it is not new unseen qualification.
Raw frames, predictions, labels and logs remain ignored/local. Curated protocol,
source hashes, gate results and failures are in `camera-multiview-pc-evidence.json`.

The next hypothesis changes from target coverage to **complete scene coverage**:
when a neighboring tool is uncertain, try one fresh calibrated view and keep
the original freshness, fit and clearance gates. Require a valid complete
selected view; do not ignore the neighbor. Freeze that candidate before a new
prospective cohort. Preserve the independent wrench grip-loss problem; do not
change physics or relax the grip indication to hide it. Approach/grasp/withdrawal
recovery and task-layer camera integration remain required before promotion.
The workbench and local speech/camera-answer path remain running. A user-controlled
microphone check has been requested; the agent has not activated recording.
