# Scene-level PC camera recovery remains unqualified

2026-10-12, baseline `5aafd82`. **50/54 complete prospective journeys pass
(92.59%), below the unchanged 95% gate. No public camera motion is promoted.**
The result and all four failures remain recorded. An independent physical audit
reconstructs all 54 verdicts. The Wilson 95% interval is 82.45–97.08%; the
different seed prevents a causal success-rate comparison with the earlier 51/54.

## Hypothesis, implementation and judge

The target-only experiment missed uncertainty in neighboring tools. The bounded
scene hypothesis therefore reuses the existing calibrated side camera once when
the primary neighboring-tool observations fail the same 0.8 fit, freshness and
supported-volume gates. Every required neighbor must qualify from the complete
alternate frame before that frame is selected. Partial views are not merged.
If the alternate view also fails, the original planner retains its original
ambiguity refusal, clearance constraints and explicitly labeled/bounded stationary
scene prediction behavior. An ambiguous identity never becomes a cached identity.

The feature remains behind `alternate_view=False` by default. Disabling the flag
is rollback. There is no new IK solver, force/friction/gain change, object pose
edit, held-object weld, model weight or nominal rack-position fallback. The
held-object pose is still inferred, not measured by this change.

All 18 validation journeys pass, with 12 fresh-camera returns and seven selected
alternate scene views. Three additional guards verify complete alternate-frame
selection, refusal when both views are ambiguous, and refusal to combine partial
views. Full regressions: **257 pass**, protected upstream hashes **46/46**.

Sources, physical judge, protocol and runtime were frozen before generating
seed **2026101302**. The distribution and 54-case tool/journey balance match the
previous predeclared training-distribution recipe. No case was filtered,
replaced or tuned after evaluation. The fixture SHA256 is
`d2de78089c7f1d886f5c67a2d4453c715b900cd85cd855f223231923a47bd9e8`.

The independent gates remain >=80 mm lift, <35 mm placement, <40 mm resting
height, <30 mm/s resting speed, <4 mm unrelated-tool center disturbance, completed
release/withdrawal and measured open fingers on both required legs. The short
pause is 0.608 simulated seconds with the existing 0.03 rad criterion. This does
not replace the distinct six-case 32-second protocol's 0.02 rad/10 mm/130 mm gates.
Neither establishes live spoken Stop or hardware safety.

## Prospective outcomes

| Measure | Result |
| --- | --- |
| First-leg physical lift and resting placement | 52/54 |
| Complete journeys, including required returns | **50/54 — FAIL** |
| Fresh-camera return attempts | 34 |
| Selected alternate scene views | 8 |
| Selected alternate target observations | 1 |
| Independently reconstructed stored verdicts | 54/54 agree |

- **000, screwdriver return:** grip indication disappears. At failure, XY error
  is 34.85 mm, but height is 162.84 mm and speed 0.947 m/s. It is not placement.
- **009, screwdriver return:** neighboring wrench remains ambiguous; no placement
  plan is authorized. The screwdriver stays about 216 mm high and 415 mm from
  its rack. The source frames are not merged or replaced with an assumed identity.
- **014, hammer resume journey:** the Cartesian lift would change IK branch beyond
  the existing per-step guard. Lift is only 0.242 mm, so the actor holds and fails.
- **029, hammer delivery:** both target-view attempts fail the geometric observation
  gate. No pickup motion occurs; the case remains a coverage failure.

Case IDs repeat between cohort directories, but their coordinates/seeds differ.
Both this 54-case cohort and the earlier 54-case cohort are now evaluated evidence,
never future unseen qualification. Raw images, predictions, labels and logs stay
local under ignored `runs/pc-camera-scene-*`. Curated source hashes, recipe,
metrics and failures are in `camera-scene-pc-evidence.json`.

## Diagnosis and strategy change

After two failed prospective optical strategies, no further view/fit expansion
or parameter sweep is proposed. A separate posthoc replay of the four already
evaluated failures records robot proprioception, contacts and physical labels
without sending any labels to the actor. It is not a replacement qualification.
Privileged tool-state methods are denied to the actor during replay.

The screwdriver return reaches **76.70 mm** error between rigid held-center
inference and physical truth. More significantly, error is **56.75 mm while the
23.36 mm jaw gap still satisfies the supported-handle proxy**, during descent.
The tool is then moving 0.633 m/s. A closed gap cannot establish a held pose.
The successful first leg's peak error is 18.97 mm. Peak joint speeds are similar:
1.111 rad/s on the successful leg and 1.119 rad/s on the failed leg. These data
do not identify speed as the cause and do not justify a blind speed/gain sweep.

The earlier held-pose audit already rejected two image fits on all 12 airborne
views of a validation scene. That evidence is retained rather than repeating a
third fit. Its small future-outcome model also failed the 10 mm p95 gate, and
its training set lacked deliberate reorientation experience.

Current PC preflight confirms the existing dataset hash, 1314 rows/76 features,
1044 training and 270 validation rows, no test rows and disjoint scene splits.
There are still **zero deliberate-turn training legs**. Actual CPU Torch2.7.1
forward/backward kernels pass in the existing pinned environment. This is a
learning-runtime preflight, not curriculum collection, a fitted model or a GPU
policy fallback. The actual pretrained pi0.5 policy remains GPU-only.

The next research action is the already-frozen training-only orientation
curriculum in `release_reorientation_protocol.json`, retaining its one remaining
bounded model-fit budget and every original validity/physical gate. Check recipe
compatibility and collect missing experience before fitting. Require full-loop
evidence and a new prospective split before any promotion. All-phase recovery,
camera task-layer integration and human/live responsiveness remain required.

## Reproduce

In the prepared WSL environment, from the extension root:

```bash
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/fresh-scene-freeze.json \
  --protocol fixtures/camera_scene_multiview_protocol.json --freeze
.venv-linux/bin/python scripts/generate_camera_reserved.py runs/fresh-scene-cases.json \
  --protocol fixtures/camera_scene_multiview_protocol.json --manifest runs/fresh-scene-freeze.json
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_camera_delivery.py runs/fresh-scene-results \
  --fixture runs/fresh-scene-cases.json --split heldout --recover-ik --verify-motion \
  --release-fallback --linear-lifts --center-grasp --safe-handoff --alternate-view \
  --return-after-delivery
.venv-linux/bin/python scripts/audit_camera_journeys.py runs/fresh-scene-results/results.json \
  runs/fresh-scene-results/audit.json --protocol fixtures/camera_scene_multiview_protocol.json
```

This reproduces evaluated evidence. The earlier target-only recipe is reproduced
at `5aafd82`, not with this changed actor. The hardware geometry inventory was
independently recompiled on the PC and matches its historical masses/bounds;
hardware access and simulation stepping were not performed by that inventory.
Hardware selection/actuation remains unauthorized. The public workbench remains
running; user-controlled microphone verification is still pending.
