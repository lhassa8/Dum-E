# PC reorientation curriculum: experience added, model rejected

2026-10-12, baseline `c9771e9`. The prepared training-only curriculum is now
implemented and collected on the PC. Its **one remaining bounded model fit fails
the unchanged offline gate**. No predictor is selected, no learned correction
is enabled, and the model-fit budget is now **0 remaining**. The frozen protocol's
original budget value records preregistration; it is not permission to refit.

## Hypothesis and bounded implementation

The earlier rejected model had zero deliberate-turn training states, while
validation included reoriented release. The expected improvement was better
prediction of changed-grasp release consequences after supplying that experience.
The judge stayed p95 XY error <10 mm, zero withheld rows, complete selection
coverage, batch-of-nine p95 inference <10 ms and positive mean placement gain.
Failure means retaining the model as rejected/local, not enabling it or tuning.

`release_reorientation_protocol.json` fixes the training scene order, four
cardinal body yaws and same request on both legs. The planner now has an optional
preferred yaw; its default is None. An explicit request selects only that
supported orientation and still requires the original scene, clearance and IK
gates. It cannot silently fall back to a different orientation. Seven tests
cover supported choices, unsupported angle, unreachable pose and blocked
clearance. No physics, solver, gripper gain, force limit or observer gate changed.

Only training scenes receive these requests. Validation uses the normal planner;
test layouts are excluded. Failed trajectories remain recorded. The four-scene
pilot supplied six release states with exact normal/repeated integration-state
agreement; the fourth scene lost grip indication and was retained as refused.

The collector snapshots complete physical integration state only for offline
counterfactual branches. Camera/robot/action features are formed before labels
are read. Nine existing ±20 mm XY actions, normal continuation and repeated zero
action are evaluated physically. Resets are not deployed actor inputs, live
object teleports or claims of successful manipulation.

## Full collection and baseline correction

All **90 non-test scenes** were processed. The dataset contains **127 release
states / 1143 action rows**: 873 training and 270 validation rows. There are
**97 reorientation training states**, of which 74 commanded changes exceed
0.035 rad. Twelve refused legs remain in the audit; unavailable follow-on legs
are not manufactured. All 127 normal/repeated state checks agree exactly.

The initial audit against the historical dataset failed: validation features
and labels differed (largest feature difference 17.8435; label difference about
19.986 mm). That comparison was not waived. The historical data predates current
controller/runtime changes, so it cannot prove unchanged current-PC validation.
A current-PC baseline was collected with no curriculum and only validation
scenes. The new audit matches **all 270 validation feature/label rows exactly,
maximum error 0**, with the same 1e-8 tolerance. Train/validation scene splits are
disjoint; no test rows or validation augmentation appear.

Dataset SHA256:
`f8af4801771bc06c7499890704e89891f132c061b8d928bc18887278311bbfb9`.
The full, pilot and split-only datasets are distinguished in metadata; the
trainer refuses limited pilots, selected split subsets, missing training or
validation rows. These are collection/audit results, not policy qualification.

## Single fixed CPU fit

The unchanged 76-feature model uses three 9413-parameter members, fixed seeds,
300 epochs and the existing training-only heading-dropout copy. The 873 training
rows become 1746 augmented rows; validation remains 270 rows / 30 groups. Actual
CPU Torch2.7.1+cu126 training took **5.261 s**. CPU selection is explicit and does
not change the GPU-only pretrained pi0.5 policy.

| Predictor | Covered XY RMSE | Covered XY p95 | Withheld rows | Selection coverage | Mean selection gain |
| --- | --- | --- | --- | --- | --- |
| Per-tool mean | 12.13 mm | 22.92 mm | 0 | 0% | None |
| Linear | 41.38 mm | 71.35 mm | 0 | 10% | +3.92 mm on selected groups |
| Neural ensemble | 14.02 mm | **22.15 mm** | **76** | **60%** | **-3.90 mm** on selected groups |

Neural batch-of-nine inference median/p95 is 0.174/0.201 ms over 30 groups. Speed
does not rescue failed quality/coverage/gain. Its rigid baseline RMSE on the same
covered rows is 13.85 mm. No validation row violates the original normalized
feature limit of 8; the ensemble's uncertainty guard accounts for withholding.
Neither that guard nor the 8 mm ensemble-XY-standard-deviation limit was widened.
P95 is reported on covered rows, not represented as coverage of all 270.

The historical 11.109 mm p95 and this 22.145 mm p95 use different validation
trajectories; they are not a causal before/after curriculum comparison. The
curriculum replaces training orientation choices with cardinal requests, so the
inherited-pose operating distribution may still be underrepresented. This is a
hypothesis, not a diagnosis established by another fit. The budget is exhausted.
Recipe metadata records training exposure, not accepted accuracy or physical
success. Weights remain local under ignored `runs/`; no application asset changed.

## Reproduce the collection; do not refit as a new sweep

From the extension root in the prepared WSL environment:

```bash
MUJOCO_GL=egl .venv-linux/bin/python scripts/collect_release_data.py runs/new-curriculum-data \
  --recovery-profile --reorientation-curriculum fixtures/release_reorientation_protocol.json
MUJOCO_GL=egl .venv-linux/bin/python scripts/collect_release_data.py runs/new-validation-baseline \
  --recovery-profile --split validation
.venv-linux/bin/python scripts/audit_release_curriculum.py runs/new-curriculum-data \
  runs/new-curriculum-data/audit.json --baseline runs/new-validation-baseline
```

The recorded single fit used the pinned policy environment's Python with
`PYTHONPATH=src`, `train_release_model.py`, and `release_sensor_dropout.json`.
Its rejected dataset, weights, raw branches and logs remain local in
`runs/pc-release-curriculum-*`; curated metrics/audit are in
`release-curriculum-pc-evidence.json`. Existing checkpoints remain unchanged.

Full regression result: **264 tests pass**; protected upstream hashes **46/46**;
changed-file lint/format pass. Public camera motion remains unpromoted at its
failed prospective gates. The next strategy must address closed-loop grasp-state
and motion evidence rather than further optical or outcome-fit sweeps. All-phase
task recovery, camera integration, live responsiveness and the human demonstration
remain incomplete; the sustained goal stays active.
