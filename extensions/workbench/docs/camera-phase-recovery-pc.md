# Experimental recovery across camera task phases on Windows

The same three known validation layouts improved from **9/27 to 25/27**
complete physical journeys after 32 simulated seconds of interruption. This
is progress, not qualification: two hammer journeys still fail, the layouts
were already evaluated, and this does not measure live acoustic Stop latency.
The public camera profile remains unpromoted.

## Baseline, hypothesis and bounded change

Baseline `runs/pc-camera-phase-baseline-001` resumed only a confirmed held tool.
All three layouts passed interruption in lifting, moving and placing; all six
other phases refused. Frozen protocol `fixtures/camera_phase_recovery_protocol.json`
SHA256 `d0943fcce0799fe061b3874fcd18186573e0566c3c532b8fcb14c32e612c298e`
specifies the nine phases, existing validation cases, profile and judges.

Hypothesis: an empty hand can retract and rescan; an interrupted tabletop grasp
can open and reacquire; an intentional release can finish without regrasping.
`CameraDelivery(phase_recovery=True)` enables these routes. Defaults are unchanged;
rollback is leaving the flag off. Held motion retains the existing gripper-gap
gate. Tabletop grasp recovery requires TCP height between 15 and 65 mm; this
is a simulation-specific workspace assumption, not proof that a real object
is supported. After opening, the hand must be confirmed open before withdrawal.
Retraction uses the current robot pose and existing Cartesian path guard.
Fresh camera pickup retains all freshness, fit, workspace and normal gates.
The original rack destination survives the rescan; scene estimates are cleared.
No learned correction, object pose write, gravity change or gain change is used.

Intentional release resumes its existing generator. Withdrawal requires an
open hand; reopening during the release phase continues the planned release.
Unknown phases, lost grip and noninterrupted resume fail while holding. Recovery
subphases are not included in this nine-phase protocol; a second interruption
inside an unsupported recovery subphase refuses rather than claiming coverage.

## Measured complete journeys

Run `runs/pc-camera-phase-recovery-001`, reproduced on final reviewed source in
`runs/pc-camera-phase-recovery-final-001`, passes approach 3/3, lowering 2/3,
grasping 2/3, lifting 3/3, moving 3/3, placing 3/3, releasing 3/3,
withdrawal 3/3 and awaiting independent placement check 3/3.
Both failed rows remain in the result. Each successful row requires the original
80 mm physical lift, 35 mm placement, resting height below 40 mm, resting speed
below 30 mm/s, unrelated-tool displacement below 4 mm, measured open fingers,
and actual actor release/withdrawal completion. The actor says
`released_unverified`; only the independent evaluator checks placement.

The 32-second interruption judge retains the gripper command and checks joint
drift below 0.02 radians and held-tool translation below 10 mm. Held phases
trigger above 130 mm. The separate original six-case long-hold protocol retains
its stronger minimum-height-throughout-hold requirement. Privileged object
access (`bench.observe`, `tool_support_height`) is denied to the actor; the
saved observer is available only to the evaluator. Raw traces stay local.

## Two similar failures: investigate before retrying

Post-hoc `scripts/diagnose_phase_retraction.py` replays only the two already
evaluated hammer failures; it is not another qualification set. Despite the
script name, diagnosis `runs/pc-camera-phase-diagnosis-002` establishes that
**empty-hand retraction succeeds; the new pickup's lifting path is refused**.
The fifth joint's waypoint changes are 0.0843505 and 0.0750659 radians, exceeding
the unchanged 0.075 guard at waypoints 28/44 and 27/43, near TCP heights 163.38
and 160.81 mm. Solved waypoint errors are 0.541 and 0.460 mm. The probe verifies
that qpos, qvel and controls remain exactly unchanged during diagnosis.

This establishes a path sampling/continuity limit, not proof of a mathematical
IK branch jump. Do not merely widen the guard, retry identical recovery, or
fit another held-pose/outcome network. Next motion work should evaluate a
bounded continuity-aware path planner with independent swept clearance,
joint tracking and complete pickup/release judges. Existing fit budget is zero.

## Reproduction

From `extensions/workbench` in the existing WSL environment:

```sh
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_phase_recovery.py runs/new-baseline
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_phase_recovery.py runs/new-recovery --phase-recovery
MUJOCO_GL=egl .venv-linux/bin/python scripts/diagnose_phase_retraction.py runs/new-diagnosis
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_pause.py runs/new-longhold --hold-profile shared
```

Each output directory must be new. No microphone, model download, simulator
solver change or hardware action is involved. See adjacent evidence JSON for
the exact regression and unchanged long-hold results.

Final validation: 273 regression tests pass (20 existing dependency warnings),
46 protected upstream file hashes unchanged, changed-file Ruff checks pass,
original long-hold/continuation 6/6. Main Windows workbench remains ready on
port 8876 with the existing LM Studio backend.
