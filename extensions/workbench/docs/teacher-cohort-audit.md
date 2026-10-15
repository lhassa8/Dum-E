# Broader teacher collection: four of twelve complete passes

The frozen training cohort completes all12 planned task/state combinations:
tasks0/1/2 × training states1/2/3/4. Only4/12 pass the complete original grasp,
hold, placement, release and budget gates. This rejects the current geometric
teacher as a general source for the planned three-task adaptation. No weights
have been trained and no learned-policy improvement is claimed.

| Task | Complete passes | Failure evidence |
|---|---:|---|
|0: between plate and ramekin|4/4|None;214/211/213/211active steps|
|1: next to ramekin|0/4|Three lifted bowls lack bilateral grasp; fourth stalls during descent until220steps|
|2: table center|0/4|All reach release but exhaust220steps during retreat; no completed settling witness|

The four passes satisfy original80mm lift,10mm held translation,20mrad joint
range and bilateral pad contact. Complete placement additionally requires native
goal, physical plate support, no gripper contact and stable final0.5sim seconds,
with35mm placement/5mm resting movement limits. Validation5/6, final7/8 and old
evaluation0 are untouched. No thresholds, budgets or controller gains change.
The same frozen configuration finishes all12 cases; it is not retuned while
collecting. A contact diagnosis begins after the first two similar task1 failures.

Exact replay of task1/state1 matches all98 recorded step positions, joints,
contact/success predicates and times, with zero reference error. Among282 native
samples lifted at least80mm, right-pad contact occurs282times, left-pad contact
zero times, and bilateral grasp zero times. Bowl contacts include the neighboring
ramekin and right finger body/pad. This supports investigating contact geometry
and neighboring-object interference, not accepting lift alone as a grasp. The
raw sample counts and reference checks were independently recomputed.

The independent cohort auditor accounts for all12cases, audits the four complete
passes and explicitly marks eight failures excluded from training. Its
`audit_completed=true` is distinct from `passed=false`. Failure rows retain their
errors and action counts. Actual ordered front/wrist videos are saved locally
for the four passing episodes. Final renders for earlier task1 failures were
inspected. Raw trajectories/observations/videos remain local under
`runs/grasp-adaptation/training-cohort-001/`.

## Labels and normalization limitations

The four complete episodes contain849active actions, yielding793unpadded8×7
windows with pause-crossing windows excluded. The local manifest explicitly
lists all eight rejected episodes. These are four episodes from one task,
not793independent samples or a three-task dataset. Do not randomly split their
overlapping windows or quietly narrow the adaptation objective to this task.

`normalize_grasp_action_targets.py` verifies original checkpoint revision
6d0231af0e48c5985f1ff86908f4674b84bc049b and publisher statistics SHA256
3f8b7854c8634ea6ccfd6ef6b8f983e3b30b067c2cdaf690b152c0899d5d9282.
It inverts native gripper+1closed/−1open into publisher0closed/1open, then uses
the original masked BOUNDS_Q99 transformation and clipping. Unclipped values
round-trip within1e-6; gripper labels round-trip exactly. However656 of6344
overlapping z-rotation labels clip, with maximum native OSC difference0.0157021,
equivalent to0.007851rad commanded rotation. Exact teacher imitation through
these normalized labels is unproven. Raw labels remain preserved separately.
Pilot397-window and broader793-window normalized arrays stay local. No training
loss, adapted checkpoint or reserved-state rollout exists.

## Strategy change: inspect published demonstrations

Before more geometric grasp tuning, inspect LIBERO's existing human teleoperation
demonstrations against our physical contact/hold/release criteria. The pinned old
Box spatial archive returns404. Current
[official download code](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/libero/libero/utils/download_utils.py)
instead supports the publisher's
[HDF5 mirror](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets).
Read-only metadata inspection pins revision
f13aa24a3da8c43c7225569f28c562979fa0e35a, Apache2.0 metadata, and the relevant
three task files totaling1,769,993,928bytes, each with publisher LFS SHA256.
No dataset bytes have been downloaded or replayed yet. About428GB free disk
was measured before considering this acquisition.

Next verify those files, inspect episode/native-state identity and exclude any
validation/final states before using them as adaptation supervision. Published
demonstrations must pass our native physical checks; task-success labels alone
do not establish secure interrupted holding. The public workbench remains
separate and unchanged. The larger goal remains active.
