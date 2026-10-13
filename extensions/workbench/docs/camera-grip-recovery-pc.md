# Context-aware grip monitoring and bounded reacquisition

The frozen camera candidate meets the observed95% gate on a new cohort:
**53/54 complete journeys (98.15%)**. One screwdriver return refuses an ambiguous
neighboring wrench. This qualifies one offline candidate cohort; public operation
remains unpromoted, and live voice, new recovery-phase interruption and human
demonstration work remain outstanding.

## Baseline and failed assumptions

Published1c77eab camera profile passes51/54 on seed2026101303. Its grip proxy can
remain positive after finger contact is lost. Robot-only gap-change braking was
tested on two evaluated failures with a fixed2mm shrink trigger. Both arms hold
with very small joint drift over32 simulated seconds, but both tools fall to
the bench. Their minimum heights14.56/19.45mm and lost contacts reject retention.
No physics freeze, object edit or optimistic held-tool success is used.

The first optional reacquisition prototype holds for3.2s, requires an inferred
empty hand plus fresh supported-tool camera evidence, then repicks once. The
same54-case retrospective replay falls to50/54: it recovers wrench025 but
refuses two previously successful returns001/049. Their2.81/3.09mm gap changes
occur during initial tabletop lift, where contact is settling. In001, the tool
remains on the table with both fingers contacting it. This contradicts treating
every gap change as free-space loss. Raw failures and independent traces remain
local; no threshold sweep or model fitting followed.

## Bounded change

Optional `recover_grip=True` requires safe handoff, verified motion and linear
lifts. The2mm shrink trigger now applies only when both before/after robot TCP
heights exceed100mm, beyond the supported15–65mm grasp region. This is a declared
simulation-specific context gate, not a calibrated hardware height. The original
15–70mm supported-handle gap gate stays active at every height. Default is off.

On unstable grip, cancel the queued carry and use the original gravity-supported
joint hold. Continue closing command for100 existing32ms physics frames (3.2s),
yielding each frame. Do not claim that braking retained the object. Opening is
permitted only with finite, closed-command gap<15mm and a fresh accepted camera
observation in the original supported tabletop volume. The existing fit,
freshness, normal, workspace and alternate-view gates are unchanged. Ambiguous
evidence or a possibly held handle refuses automatic opening.

After28 opening frames, retract the empty hand, resurvey and run the existing
pickup/delivery actor with the original destination and rack context. At most
one grip reacquisition per leg is allowed, separately from the existing one
postrelease placement correction. A second unstable grip fails while holding.
No tool pose, velocity, contacts, actuator gains or gravity change enters this
route. Object truth is denied to the actor; diagnostic contact labels remain
evaluator-only. Rollback is leaving recover_grip off.

## Validation and prospective evaluation

| Evaluation | Full journeys | Meaning |
| --- | --- | --- |
| Published profile, seed2026101303 | 51/54 | Previously evaluated baseline |
| Unconditional gap-trigger prototype | 50/54 | Rejected retrospective experiment |
| Context-aware monitor, same cohort | 52/54 | Retrospective improvement, not unseen |
| Frozen new seed2026101304 | 53/54 | Prospective observed gate met |

The same-cohort improvement completes the formerly failed wrench025 redirect
at22.148mm from its rack. Wrench046 still refuses fresh camera evidence after
loss; hammer005's existing postrelease-camera refusal remains. All54 replay
verdicts independently reconstruct. Raw `split=heldout` is inherited from the
old fixture; after its earlier evaluation, this replay is explicitly retrospective.

Before generating the new54 cases, frozen sources/runtime include actor, robot,
perception, optics, physics, planner, judge, generator and protocol. FixtureSHA:
eae7dcfdf07f849c0c57d2e4addeb1824deca9aca5d6807d08621dea8e68c81c.
All cases generated once, counted without replacement or filtering. Original
80mm lift,35mm placement, resting height40mm/speed30mm per second, open fingers,
completed release/withdrawal and unrelated-tool4mm limits remain. Both required
legs are counted; a physically lifted tool alone cannot pass.

New cohort: first-leg physical54/54, full53/54,36 return legs, seven alternate
scene views, no accepted alternate target view. One first-leg placement
correction, zero return corrections. Independent54/54 verdict reconstruction
matches; Wilson95% interval90.23–99.67%. The post-evaluation source/runtime
snapshot matches the pre-generation snapshot exactly. Different seeds prevent
a causal rate comparison against the older cohort.

**No grip-loss event or reacquisition occurs in the new cohort.** It evaluates
the complete camera candidate, not unseen grip-loss recovery. The positive
reacquisition evidence is the known025 replay. Do not broaden that claim.

The one prospective failure003 completes delivery but return planning refuses
an ambiguous wrench while holding the screwdriver216.2mm high,391.2mm from its
rack. Independent post-hoc32s hold passes: maximum joint drift.000102rad,
tool translation.304mm, minimum height215.90mm, gripper command and both finger
contacts retained. It remains a failed return, not a completed journey.

Known nine-phase/three-layout32s validation remains27/27; original long-hold
resume/return remains6/6. All287 regression tests pass (20 dependency warnings),
46 protected upstream hashes match, changed-file checks pass. Guards test
nonfinite/possibly-held gaps, retry exhaustion and retaining the binary grip
gate during tabletop settling. No model fit; exhausted fit budgets stay0.

## Remaining work and reproduction

The original nine-phase protocol does not cover Stop/resume inside the new
settling/opening recovery subphases. Current resume can refuse after an empty
gap during recovery. Test and resolve those states before live integration.
The candidate also does not establish hardware drop safety, collision clearance
for arbitrary obstacles or95% population reliability from one small cohort.

Existing WSL environment, fresh output directories:

```sh
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_phase_recovery.py runs/new-phase --phase-recovery --refine-cartesian --verify-release --recover-grip
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/new-candidate/frozen.json --freeze --protocol fixtures/camera_grip_recovery_protocol.json
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/new-cohort/fixture.json --manifest runs/new-candidate/frozen.json --protocol fixtures/camera_grip_recovery_protocol.json
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_delivery.py runs/new-cohort/evaluation --fixture runs/new-cohort/fixture.json --split heldout --return-after-delivery --recover-ik --verify-motion --release-fallback --linear-lifts --center-grasp --safe-handoff --alternate-view --phase-recovery --refine-cartesian --verify-release --recover-grip
.venv-linux/bin/python scripts/audit_camera_journeys.py runs/new-cohort/evaluation/results.json runs/new-cohort/audit.json --protocol fixtures/camera_grip_recovery_protocol.json
```

Reusing the protocol seed reproduces already evaluated coordinates. Raw traces,
models and images remain local; no microphone, external model call or hardware.
