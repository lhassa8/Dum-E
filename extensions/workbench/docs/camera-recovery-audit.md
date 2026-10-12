# D2d: camera and motion recovery — experimental

October 11, 2026. Full goal remains active. Public A4 voice assistant is unchanged;
these opt-in camera controllers are not connected to the public app.

## Outcome and acceptance

On the frozen 18 C3 validation journeys, final conventional camera recovery and
recovery plus the unchanged experimental release model both pass **17/18**.
This is progress over C3's 16/18 conventional and 14/18 learned runs, but **fails
our 95% full-journey gate**. Validation-016's wrench redirect lands 36.424 mm from
its requested position, outside the unchanged 35 mm limit. Both final policies
complete 12 fresh-camera returns. Mean initial placement error among the same
17 passing placements is 12.261 mm conventional versus 10.548 mm learned.
This does not establish an accepted learned controller or generalization.

The final runs strengthen the neighbor judge: maximum body-center translation
sampled at every 32 ms motion/hold frame across both legs, rather than only final
displacement. The 4 mm limit is unchanged. Sub-frame collisions, tool-tip motion
and rotation are not separately judged. Earlier C3 results used the older judge.
All 24 new C3 test layouts remain unopened because validation still fails.

## What the evidence changed

- **Shadow, not viewpoint:** the two previously missing wrench observations were
  exposed but dark under the arm. A second camera did not restore them. Separate
  shadow fitting preserves the original bright-metal pass and ambiguity handling.
  A limited tilted-face fit uses measured depth planes with upward normals within
  about 18 degrees of vertical. Source pixels, fit threshold 0.8 and fresh-target
  age limit 0.25 simulation seconds are unchanged. Protected D1 regression: all
  72 clear tools found, position p95 0.257 mm, maximum 0.404 mm; all 12 occluded
  cases withheld. This is known-color primitive geometry, not recognition of real
  screwdrivers or arbitrary tools. Alternate camera remains probe-only.
- **Bounded robot-only IK recovery:** when current-seed kinematics fails, a home
  seed is solved in a separate buffer. Independent forward kinematics must meet
  0.8 mm and 0.008 rad; real joint state and commands are not teleported. Verified
  endpoint tracking waits a bounded 60 extra frames, then holds/refuses beyond
  provisional 15 mm / 0.035 rad bounds. A reachable endpoint is not a proof of a
  collision-free path.
- **Wrist saturation diagnosis corrected:** a 128-sample trace at 2 ms resolution
  alternates +12/-12 Nm 127 times, with zero mean torque and only 1.433e-5 rad net
  joint drift over 256 ms. This is numerical servo chatter/aliasing, not evidence
  of sustained overload. Raw model inputs and the normalized-input guard of 8
  remain unchanged. No force caps, gains or physics were changed.
- **Camera-derived handoff orientation:** independent contact diagnostics show a
  wrench butt overlapping the screwdriver tip during descent. A catalog-footprint
  planner chooses a supported orientation using observed neighboring poses.
  Empty-hand preflight survey helps retain a scene view before pickup. When a
  neighbor is subsequently occluded, a labeled stationary-scene prediction may
  use its previously validated camera observation for at most 30 simulation
  seconds. Its uncertainty allowance (0.5 mm + 0.2 mm/s) is provisional and not
  calibrated. Contradictory positions, ambiguous observations, invalid numeric
  values, never-observed neighbors and stale history refuse planning. Pickup
  targets still require a fresh observation. This assumption needs further
  testing; it is not continuous tracking or a collision guarantee.
- **Honest model refusal:** deliberate reorientation changes the release recipe
  relative to training. The unchanged model refuses those actions. An explicitly
  labeled conventional fallback requires verified motion, grip and geometric
  clearance. A supported but predicted unsafe future cannot be overridden.
  Three final learned-run legs use changed-recipe fallback. No refit this slice.

Straight Cartesian lifts, encoder centering and held-tool survey detours did not
solve the full loop; their failed runs are retained. Final profile enables none
of those optional experiments. The remaining redirect failure indicates changed
held geometry after reorientation; increasing the placement limit or blindly
adding a correction would not demonstrate learned capability.

## Responsiveness and checks

An isolated, sequential 30-frame benchmark of one stationary scene measures
RGB-D capture plus localization at median **77.245 ms**, p95 **82.512 ms**;
first frame 97.564 ms. Capture is median 8.847 ms, localization 68.445 ms.
This excludes motion, IPC, disk writes, speech and the public application.
It is a modest cost increase from the earlier simpler perception pipeline and
must be considered before enabling continuous camera use.

Root suite: 175 tests passed; independent exported-fork suite: 156 passed.
Ruff and formatting pass for 93 lab and 69 fork Python files; all 46 pinned
upstream source hashes match. A restricted test run lacked macOS graphics/local
IPC access; the native-access rerun passed without skipping or weakening tests.
Results are recorded in `camera-recovery-evidence.json`. The actor only
reports `released_unverified`; a separate physics verifier judges placement.

## Reproduce

From `Dum-E/extensions/workbench` (or the lab root):

```sh
uv run --locked python scripts/verify_camera_delivery.py runs/recovery-reproduction \
  --fixture fixtures/release_model_cases.json --split validation \
  --recover-ik --verify-motion --safe-handoff --return-after-delivery
```

For the experimental learned comparison, add:

```sh
--release-fallback \
--release-model src/physical_ai_lab/assistant/assets/learned/release-outcome-v2-experimental.npz \
--release-kind ensemble
```

The fixture, model artifact and gates retain their published hashes. Raw runs
remain under lab `runs/`; bounded results, failures and diagnostic traces are
included in `camera-recovery-evidence.json`. See `camera-recovery.png`.

## Next bounded slice

Collect training evidence for deliberately reoriented grasps, or measure actual
held-tool geometry, before further release-model use. Judge the whole 18-case
loop before opening the 24 new tests. Implement camera Stop/resume/replan across
all phases before public integration; current camera resume supports held phases
only. Preserve the working public voice interaction throughout.

Camera-informed public workflow, useful full-loop learning, all-phase recovery,
cold language-model response, audible onset/noise/live responsiveness, hardware
adaptation and the user's convincing live demonstration remain unfinished.
