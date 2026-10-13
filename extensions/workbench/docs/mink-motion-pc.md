# Maintained IK behind the camera workbench — PC experiment

Mink 1.3.0 now runs complete camera-controlled tool journeys through the existing
Dum-E interface. The frozen comparison passes 12/12 physical legs for both
Mink and the original solver. Six Mink Stop tests each hold the tool for
32 simulated seconds, with maximum joint drift 0.000252 radians and tool drift
0.331 mm. These are two default-layout seeds, not broad held-out qualification.

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

Next: prospective varied-layout journeys with this backend, cancellation during
planning, and the full acoustic/acknowledgment measurements. Preserve the existing
baseline while those gates remain outstanding. Pretrained VLA adaptation is a
separate step; this IK library does not itself learn manipulation skills.

Curated [evidence](mink-motion-evidence.json) records source hashes, dependencies,
physical bounds and interface results. Raw traces and rendered images remain
under `runs/mink-motion-001` and `runs/mink-live-*` on this workstation.
