# Complete training demonstrations: released bowls resting on plates

The calibrated simulator teacher completes grasp, lift, interrupted holding,
transfer, release and retreat in both task0 training states1/2. This extends
the [grasp-only evidence](grasp-teacher-audit.md) through the task named by the
prompt. No learned weights have changed; no public controller is promoted.

Before execution, the [protocol](grasp-adaptation-protocol.json) specifies the
placement target, bounded20mm translation commands,12release steps,21settling
steps,35mm placement limit and5mm resting movement limit. Initial plate center
and collision height plus measured held-bowl-to-EEF geometry determine the
teacher target. Native OSC alone executes the actions. No object edits, welds,
pose freezing, altered torque caps or evaluation-state access are used.

The original grasp/hold stage is preserved. Holding uses kp300/damping2 for
more than1sim second and at least2wall seconds. Original80mm lift,10mm
translation,20mrad joint-range and bilateral pad-contact gates remain. The
220active-step limit includes transfer, release, retreat and settling; the
explicit pause remains excluded as in the existing interruption protocol.

## Completed placement assay001

| Training state | Active steps /220 | Minimum held lift | Placement XY error | Final resting movement | Complete teacher |
|---|---:|---:|---:|---:|---|
|1|214|115.799mm|3.729mm|0.00000187mm|Pass|
|2|211|110.925mm|7.433mm|0.0000897mm|Pass|

Both retain native task success, actual bowl/plate collision contact and zero
gripper/bowl collision contact throughout the final0.5sim seconds. This verifies
physical support after release, instead of relying on a success flag while the
gripper is closed. Native rest samples cover each2ms physics step. Native grasp
holds contain547 samples each, and last1.05sim seconds/2.717and2.951wall seconds.
The budget margins are only6/9steps; broader layouts may exceed the budget.

Independent auditing recomputes contact, task success, placement error and
resting movement from raw traces, alongside the original grasp/hold gates,
source hashes and allowed actor observations. Three negative checks alter one
final raw witness independently: gripper contact, missing plate contact, or
native goal failure. Each is rejected. An audit attempted before the second
episode finished also rejects the incomplete two-case cohort; the same live
simulator is then observed to completion, without restarting.

Actual front/wrist observations are rendered in their recorded order, inserting
the hold frames between grasp and transfer. Videos contain236/233frames at
20Hz simulated time, exclude loading/wall-clock stalls, and contain no audio.
Final placed front renders were visually inspected. Raw data and videos remain
local under `runs/grasp-adaptation/placement-assay-001/`; the published
[evidence](placement-teacher-evidence.json) contains aggregates/hashes only.

## Prepared action labels, not trained weights

The two425-action demonstrations yield397 overlapping8×7action chunks. They
contain no padding, no explicit holding actions, and no windows crossing the
pause. All397 labels independently match the raw native OSC actions exactly.
Only training states1/2 appear. Hold images and evaluator truth are excluded
from actor observation inputs. These are two episodes, not397independent tasks.
Do not randomly split their overlapping windows for model selection.

The local dataset at `runs/grasp-adaptation/action-chunks-002/` contains raw
native OSC targets, observation references/hashes and task prompts. Labels are
not yet normalized. Training must invert the publisher's binary LIBERO gripper
conversion and use the pinned checkpoint's action statistics; actions are never
interpreted as Panda joint targets. Original publisher image/proprio processing
remains necessary. No training loss, adapted checkpoint or reserved-state policy
outcome exists yet.

Next collect additional complete training episodes, then cache frozen pretrained
features and adapt the existing action head. Use state-level validation5/6 for
selection and untouched7/8 for final base-versus-adapted physical comparison.
The human room-microphone demonstration, broader camera recovery and dependable
learned-policy grasp/Stop/resume/placement remain requirements of the full goal.

## Reproduce

```sh
/home/user/.local/share/dume/libero-py38/bin/python scripts/collect_libero_grasp_teacher.py runs/grasp-adaptation/NEW --openpi runs/policy-runtime/openpi --config-dir runs/policy-runtime/libero-render-001/config --complete-placement
.venv-linux/bin/python scripts/audit_libero_grasp_teacher.py runs/grasp-adaptation/NEW
.venv-linux/bin/python scripts/prepare_grasp_action_chunks.py runs/grasp-adaptation/NEW runs/grasp-adaptation/NEW-DATASET
```

Output directories must be new. Tools run locally in the existing WSL environments.
