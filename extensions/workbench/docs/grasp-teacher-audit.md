# Native grasp teacher: two audited training states

A training-only geometric teacher now produces secure rim grasps in two new
LIBERO task0 states. This is preparation for adapting the existing pretrained
action head, not a learned-policy improvement. No weights have been trained,
and the public workbench controller is unchanged.

The prospective [split and protocol](grasp-adaptation-protocol.json) excludes
previous evaluation state0. States1–4 are training/calibration,5–6 validation,
and7–8 reserved final evaluation. Only task0 states1/2 were accessed here.
Object geometry and native contact truth belong to the teacher/evaluator;
the saved actor inputs contain only front/wrist RGB and robot proprioception.
The task prompt is stored separately. The teacher must never be imported by
the learned actor.

## Calibration and retained failures

The initial geometry survey incorrectly treated box colliders as meshes and
read mesh index−1. Its local survey001 is invalid and retained. Corrected
survey002 branches on native geometry type: metric box corners or a valid mesh
index, rejecting unsupported types. Bowl width is approximately107mm versus
76mm clear pad opening, supporting a rim grasp. Native geometry calibrates pad
centers, rim height, closing direction and the end-effector target.

Teacher assay001 reaches bilateral pad contact in both states but exhausts
the original220-step budget during lift. State1 spends57/117/12/34 steps in
approach/descent/close/lift; state2 spends47/122/12/39. Recorded EEF travel is
roughly one quarter of the commanded displacement during the long descent.
Neither trial passes; neither is training data.

After these two similar failures, the changed hypothesis is trajectory
efficiency, not a changed grasp offset or weakened contact judge. Approach
clearance becomes80mm instead of preserving the initial high EEF height.
Translation commands are capped at30mm approach and20mm descent/lift, rotation
at0.1rad; close remains3mm/12steps. Native action bounds, OSC implementation,
actuator caps,220-step budget and physical gates remain unchanged.

Assay002 passes both states but lacks persisted initial object height needed
for independent lift recomputation. Assay003 repeats the same trajectory while
recording initial truth and actual holding frames. These repetitions do not
increase the number of distinct states or establish generalization.

## Audited assay003

| Training state | Active steps | Minimum held lift | Maximum translation | Maximum joint range | Dense hold samples |
|---|---:|---:|---:|---:|---:|
|1|102|115.799mm|1.311mm|0.520mrad|547|
|2|91|110.925mm|5.227mm|0.578mrad|547|

Both retain bilateral pad contact throughout1.05simulated seconds of native
joint holding, lasting2.480/2.539wall seconds. Original limits remain80mm lift,
10mm translation,20mrad joint range, kp300/damping2. Both pass.

The independent auditor checks as-run source hashes, prospective state membership,
all193 active action vectors, observation counts and allowed fields, dense2ms
hold coverage, and recomputes lift/translation/joint/contact gates from raw
records. It renders actual recorded front/wrist images into local20Hz simulation
videos,124/113frames, with observation/video hashes. Held front renders were
also inspected. The videos exclude loading, do not represent wall-clock speed,
and contain no audio. Raw NPZs, actions, contact traces, images and videos remain
local under `runs/grasp-adaptation/teacher-assay-003/`; only aggregate evidence
is published.

This is a grasp/lift/hold prefix. The prompt requests placement on a plate,
which this teacher has not demonstrated. No release, resting placement,
resumed learned action or full tool journey is established here. Do not train
terminal zero actions against this full-task prompt or infer task completion
from the prefix. Next extend demonstrations through verified release/resting
placement before constructing complete action-chunk training episodes. Frozen
backbone/action-head adaptation and reserved-state comparison remain unperformed.

## Reproduce

From the extension, with the existing isolated LIBERO environment and checkout:

```sh
/home/user/.local/share/dume/libero-py38/bin/python scripts/collect_libero_grasp_teacher.py runs/grasp-adaptation/NEW --openpi runs/policy-runtime/openpi --config-dir runs/policy-runtime/libero-render-001/config
.venv-linux/bin/python scripts/audit_libero_grasp_teacher.py runs/grasp-adaptation/NEW
```

The output directory must be new. The audit uses the existing local
`imageio_ffmpeg` encoder. No hardware, microphone or external service is used.
