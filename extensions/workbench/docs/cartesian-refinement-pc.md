# Bounded Cartesian sampling: motion improved, placement still fails

Two previously refused hammer journeys now physically lift, carry, release and
withdraw. Both still fail the original 35 mm placement judge, at 36.334 and
35.601 mm. **Full qualification remains 25/27**, on the same already evaluated
three validation layouts and nine interruption phases. The public profile is
not promoted and both experimental flags remain off by default.

## Baseline and hypothesis

Published baseline `56a6adf`, `runs/pc-camera-phase-recovery-final-001`, completes
25/27 physical journeys. The two low-height hammer recovery routes retract
and rescan successfully, but the new pickup lift is refused at the existing
0.075-radian per-waypoint joint limit. Hypothesis: the discretization is too
coarse, rather than evidence that the same Cartesian segment is impossible.
Rollback: leave `SimRobot(..., refine_cartesian=False)`.

Robot-only read-only probe `runs/pc-camera-refinement-probe-001` tested fixed
2x and 4x counts on these already evaluated failures. Doubling 44/43 waypoints
to 88/86 reduces maximum joint steps to 0.0599094/0.0443349 radians. Quadrupling
gives 0.0286481/0.0221799. All probes leave qpos, qvel and controls unchanged.
This supports a sampling limit, not a mathematical branch-discontinuity claim.

## Bounded change and execution

Optional `refine_cartesian=True` tries the original path, then 2x and 4x counts
only if a solved waypoint exceeds the unchanged 0.075 limit. Additional retries
are capped at 400 waypoints. Unsolved IK and other errors propagate without
retry. Original IK iterations, tolerances, joint limits and seed are unchanged;
no alternate branch or home-seeded fallback is added to Cartesian planning.
Planning still finishes before any commanded tick. The actor executes every
returned waypoint over the correspondingly longer duration, followed by its
existing settling/tracking checks. It does not compress the denser path into
the original number of ticks. Default paths return the same count as before.

`runs/pc-camera-refined-phase-001`, using the original frozen phase protocol,
records exactly two sampling refinements, both doubling. Physical results:

| Measure | Recovery baseline | Optional refinement |
| --- | --- | --- |
| Complete independently qualified journeys | 25/27 | 25/27 |
| Actor finishes release and withdrawal | 25/27 | 27/27 |
| Previously failed hammer lifts | 0.372 / 0.269 mm | 244.854 / 241.305 mm |
| Hammer final target distances | 254.815 / 254.784 mm | 36.334 / 35.601 mm |

The two refined hammer cases retain open fingers, resting height 21.727 mm,
negligible resting speed and unrelated-tool displacement. Each initial
32-second interruption passes its original hold checks. A nearer placement is
not a pass: the 35 mm bound is unchanged and the actor says released_unverified.
No object pose/velocity edit, fixture substitution, contact change, model fit,
or gravity/servo modification is used. Privileged object methods remain denied
to the actor. These checks do not certify swept collision clearance or hardware
safety; they establish the measured complete simulated journeys only.

## Placement diagnosis and next action

After two similar placement failures, investigate rather than tune an offset
or fit another network. Post-hoc replay
`runs/pc-camera-refined-placement-diagnosis-001` saves object truth only in the
independent diagnostic. The held rigid estimate is wrong by 8.19/8.23 mm at
the end of lifting, 12.23/11.96 mm after transport, and **30.18/29.48 mm** at
the end of placing. Measured gripper gaps remain approximately 43.5 mm during
placing; the existing grip proxy does not detect this pose error. The last
pre-release actual XY error is 35.19/34.46 mm; settling adds roughly 1.1 mm.
Thus the dominant observed error exists before release, rather than being a
large post-release throw. No truth-derived correction feeds the actor.

Next: evaluate fresh calibrated camera evidence after withdrawal, when the
tool rests on the supported tabletop, and a bounded physical correction route.
Retain refusal on ambiguous images, complete placement/withdrawal and unrelated
tool judges, and prospective evaluation before public promotion. Held optical
and outcome-fit budgets remain exhausted; do not repeat those fits.

## Reproduction

Use the existing workbench WSL environment, fresh output directories:

```sh
MUJOCO_GL=egl .venv-linux/bin/python scripts/diagnose_phase_retraction.py runs/new-probe
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_phase_recovery.py runs/new-refined --phase-recovery --refine-cartesian
MUJOCO_GL=egl .venv-linux/bin/python scripts/diagnose_phase_retraction.py runs/new-placement-diagnosis --refine-cartesian
```

The adjacent evidence JSON records source hashes and final regression results.
Raw logs and diagnostic labels remain local. No microphone or hardware action.

Verification: all277 regression tests pass (20 dependency warnings); the original
long-hold/continuation protocol remains6/6; all46 protected upstream hashes match;
changed-file Ruff checks pass. Main workbench on port8876 remains model-ready.
