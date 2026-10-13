# Maintained IK behind the camera workbench — PC experiment

Mink 1.3.0 now runs complete camera-controlled tool journeys through the existing
Dum-E interface. The frozen comparison passes 12/12 physical legs for both
Mink and the original solver. Six Mink Stop tests each hold the tool for
32 simulated seconds, with maximum joint drift 0.000252 radians and tool drift
0.331 mm. These are two default-layout seeds, not broad held-out qualification.

The subsequent frozen prospective comparison evaluates all 54 new layouts per
backend, including randomized lane assignments, yaw and lighting, delivery,
Stop/resume, redirect, and return. Both adapters pass **52/54 full journeys
(96.3%)**, meeting the original 95% observed-success gate. Each applies 90
physical legs; 88 pass. Sources, judge, recipe and runtime hashes match before
and after the cohort. No cases were replaced or tuned against.

Mink's two failures are screwdriver returns: ambiguous neighboring wrench and
stale camera frame. Both stop with the tool held rather than report placement.
The original backend instead has one 4.457 mm unrelated-tool disturbance (above
the unchanged 4 mm bound) and one stale frame. Mink passes screwdriver 16/18,
wrench 18/18, hammer 18/18; the original passes 18/18, 17/18, 17/18 respectively.
The rates provide no overall reliability improvement. The 95% Wilson interval
is 87.5–99.0%, so this sample does not establish 95% population reliability.
See [prospective evidence](mink-cohort-evidence.json); raw data remain local in
`runs/mink-cohort-001`. Planning-time cancellation and full voice qualification
are still outstanding; the profile remains experimental.

The live typed sequence passes screwdriver delivery, conversation during motion,
Stop/resume, changing to the wrench while first returning the screwdriver, and
contextual return. All four placements have successful independent outcomes;
native task counters show 170/132/132/131 Mink pose solves. HTTP Stop to observed
stopped state is 23.28 ms in one trial; this excludes spoken timing and settling.

## Run the separate experiment

From the Dum-E repository on this Windows workstation:

```powershell
& .\extensions\workbench\scripts\launch_mink_experiment.ps1
```

Open <http://127.0.0.1:8896>. The existing main8876 and camera8886 services are
preserved. An occupied experimental port is refused before any services start.
The launcher installs pinned Mink/QP components into a separate Linux directory
and uses a frozen archive of published revision296cc6f, excluding unfinished
working-tree camera changes. Each session runs an immutable shell-launcher copy.
Closing the launcher cleans up its owned frontend and simulator.

This experiment explicitly uses CPU/int8 speech recognition to preserve the
existing GPU services. Microphone listening begins off and requires the user to
activate it. CPU speech here has not received an end-to-end timing qualification.
Both LM Studio aliases must already be available: `prism-ml/bonsai-27b` and
`workbench-vision-gemma`. The launcher discovers the current WSL gateway.

## What changed and what remains

The experiment replaces pose solving with the maintained
[Mink library](https://github.com/kevinzakka/mink), retaining the original camera
perception, task coordination, real contact physics, gravity-compensated hold,
and independent simulator judges. It preserves the original 0.8 mm/0.008 rad
IK residual limits, 120 iterations, 0.12 rad iteration cap, 0.075 rad waypoint
continuity limit, and bounded Cartesian refinement. The zero-velocity constraint
for non-arm DOFs applies only to private IK data; real tools remain free bodies.

No geometry fitting, forces, contact parameters, object poses/velocities, or
judging thresholds changed. Scene collision constraints are not enabled yet.
Some final camera checks still report placement unverified; the independent
simulation evaluator supplies the verified placement outcome. This result does
not establish sensor-only operation or real-hardware readiness.

Next: cancellation during planning and the full acoustic/acknowledgment
measurements. Preserve the existing
baseline while those gates remain outstanding. Pretrained VLA adaptation is a
separate step; this IK library does not itself learn manipulation skills.

Curated [evidence](mink-motion-evidence.json) records source hashes, dependencies,
physical bounds and interface results. Raw traces and rendered images remain
under `runs/mink-motion-001` and `runs/mink-live-*` on this workstation.
