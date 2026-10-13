# Fresh post-release camera evidence and one physical correction

The same 27 known-layout interruption journeys now pass **27/27**, versus25/27
with motion refinement alone. A new prospective cohort passes **51/54 full
journeys (94.44%)**, below the unchanged95% gate. Public camera operation is
still unpromoted; the full voice/human-demonstration goal remains active.

## Baseline, hypothesis and change

Baseline8f371bc resolves the two hammer lift refusals but leaves final placements
36.334/35.601mm from target, outside the35mm judge. Post-hoc read-only probe
`runs/pc-postrelease-camera-probe-001` finds fresh tabletop RGB-D observations
accurate to0.0565/0.0937mm, scores.9989/.9923, with qpos/qvel/controls unchanged.
Hypothesis: reobserve after withdrawal, then physically reacquire a misplaced
resting tool once. This avoids relying on the stale rigid held-pose inference.

Optional `CameraDelivery(verify_release=True)` requires existing safe-handoff
and verified-motion profiles. After opening, withdrawal and settling, use the
existing calibrated observation path, including all freshness, score, workspace
and surface-normal gates. A measured XY error<=25mm passes a visual margin
check, not a physical-success declaration. An error>25mm and<=80mm permits
one fresh pickup to the original destination; the original rack context survives.
Reobserve after that release. Larger error, unusable evidence or a second
out-of-margin result fails while holding. No threshold tuning after evaluation.
The25mm margin is stricter than the independent35mm placement criterion.

The final actor outcome remains released_unverified. Physics success still
requires measured80mm lift,35mm placement, resting height<40mm, speed<30mm/s,
open fingers, completed release/withdrawal and unrelated-tool motion<4mm.
No object-state write, weld, freeze, privileged pose feedback or model fit.
Rollback: leave verify_release off (default); phase recovery and Cartesian
sampling refinement also remain optional and off by default.

## Same-layout interruption result

`runs/pc-camera-release-correction-001`:27/27 through the original nine-phase,
three-known-layout protocol and32-second holds. Only the two previously missed
hammer cases need a second pickup; final distances9.590/9.720mm. There are29
postrelease camera checks across27 journeys. This is validation evidence, not
unseen evaluation or live acoustic Stop timing.

## Frozen prospective full journeys

Before generating coordinates, froze actor, robot adapter, perception, camera
scene, physics, planner, judge, generator, dependencies and protocol in
`runs/pc-camera-release-candidate-001/frozen.json`. Protocol
`fixtures/camera_release_correction_protocol.json`, seed2026101303, preserves
the prior training-derived distribution, tools,54-case balanced journey design,
short-hold scope and original criteria. Both required legs use the new flags.
All54 cases generated once; none filtered or replaced. FixtureSHA256:
cb2a45805efad6018e04850d5da897b83f19ea9a19f82d9590d88a09665e7a2c.

`runs/pc-camera-release-reserved-001/evaluation`: full51/54, first-leg physical
lift/placement52/54,34 fresh-camera return legs. Nine alternate scene views,
zero accepted alternate target views. There are51 first-leg visual checks,
35 return-leg checks and one return correction (zero first-leg corrections).
These counters include checks that trigger or follow correction; they are not
another success metric. The independently reconstructed54/54 verdicts match;
Wilson95% interval84.89–98.09%. Source/runtime snapshot after evaluation is
byte-identical to the preregistered snapshot. This new seed cannot establish
a causal rate improvement over earlier51/54 or50/54 cohorts.

Failures retained, with post-hoc diagnostics only:

- pc-reserved-005 hammer/resume: physically within30.254mm, resting33.399mmhigh,
  but both postrelease views report missing/weak geometric fit. Actor refuses
  verification; no return leg claimed. Do not substitute the evaluator pose.
- pc-reserved-025 wrench/redirect: grip loss during lifting for return, tool
 265.927mmhigh/.840m/s at refusal, rigid inference error72.87mm.
- pc-reserved-046 wrench/deliver: grip loss during moving, tool132.411mmhigh/
 1.217m/s at refusal, rigid inference error101.13mm.

In025, both-finger contacts at42.96mm gap become one-finger contact at34.35mm,
then no contact at22.64mm, before the15mm gap guard fails at13.90mm. In046,
no contact already exists at37.26mm; guard fails at9.14mm three32ms frames
later. These are evaluator-only contact labels. They establish late detection,
not permission to feed object contacts into the actor or assume velocity alone
caused failure. Peak joint speeds differ1.698/1.118rad/s across the two cases.
Next prioritize temporal gripper/robot-load evidence and bounded grasp recovery
before another prospective run. No more held-pose or outcome-fit sweeps.

## Verification and reproduction

All280 regression tests pass (20 dependency warnings),46 protected upstream
hashes match, original six long-hold/continuation cases pass6/6, changed-file
Ruff checks pass. Negative real-physics tests prove missing depth or stale
postrelease frames cannot start another pickup or advance physics. Fit budget0.
Raw images, traces and diagnostic labels remain local; no mic/hardware action.

```sh
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_phase_recovery.py runs/new-phase --phase-recovery --refine-cartesian --verify-release
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/new-candidate/frozen.json --freeze --protocol fixtures/camera_release_correction_protocol.json
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/new-cohort/fixture.json --manifest runs/new-candidate/frozen.json --protocol fixtures/camera_release_correction_protocol.json
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_delivery.py runs/new-cohort/evaluation --fixture runs/new-cohort/fixture.json --split heldout --return-after-delivery --recover-ik --verify-motion --release-fallback --linear-lifts --center-grasp --safe-handoff --alternate-view --phase-recovery --refine-cartesian --verify-release
.venv-linux/bin/python scripts/audit_camera_journeys.py runs/new-cohort/evaluation/results.json runs/new-cohort/audit.json --protocol fixtures/camera_release_correction_protocol.json
```

Output paths must be fresh. Reusing this protocol seed reproduces evaluated
coordinates; it does not create another unseen cohort. See adjacent evidenceJSON.
