# Stop and resume during camera grip recovery

Known recovery-interruption journeys improve from1/4 to **4/4** after32 simulated
seconds of Stop. The four pauses cover settling after unstable grip, empty-hand
opening, retraction and survey. The actor completes a physical return each time
without resetting its one-reacquisition budget. Public camera integration and
live acoustic/human-demo validation remain outstanding.

## Baseline and bounded change

Baseline81d44bd already meets the observed camera gate on its prospective cohort,
but that cohort triggers no grip recovery. The new protocol uses the already
evaluated wrench025 loss/redirect case, including its original19-frame initial
Stop and return redirect. It pauses only after grip recovery begins, then holds
for32 seconds before resuming. Three baseline refusals are retained: settling
incorrectly demands a supported held handle, opening and retraction have no
resume route. Survey alone completes, by restarting the old rescan path.

With both phase_recovery and recover_grip enabled, resume now recognizes these
four phases only while the existing one-reacquisition counter is1. It continues
the existing generator and increments motion revision; it does not start a new
episode, reset counters, discard rack context or reacquire twice. Settling must
retain the closed command and a finite0–80mm encoder gap. Opening requires a
non-carrying actor, open command and finite gap. Retraction/survey require a
confirmed open hand. Contradictory states refuse while holding. Ordinary held
motion retains its original supported-handle gate. Defaults remain off.

During post-loss settling, the object is already unstable and can fall naturally.
Continuing the closed settling command is not a claim that the tool is retained.
The subsequent empty-gap and fresh supported-tabletop camera gates still decide
whether opening and pickup are permitted. Opening interrupted after its earlier
camera check does not reuse that old pose for pickup: retraction/survey is
followed by a fresh observation before approach. No object-state changes, new
gains, reduced placement limits or learned corrections are introduced.

## Measured full journeys

Final reviewed-source run `runs/pc-grip-interrupt-recovery-final-001` passes4/4.
Final distances are22.15–22.45mm from the original rack, below the unchanged35mm
limit. All require actual80mm lift, resting height<40mm, speed<30mm/s, open
fingers, completed release/withdrawal and unrelated-tool displacement<4mm.
The evaluator denies privileged object methods to the actor.

Each32-second Stop preserves the gripper command and has maximum joint drift
at most.000140rad, against the original.02rad bound. Tool retention is deliberately
not claimed for an already lost grasp; original supported-held-tool retention
tests remain separate. All four continuations retain exactly one reacquisition.
Actor output remains released_unverified; the independent physics judge owns
the placement verdict.

Final294 regressions pass (20 dependency warnings),46 protected upstream hashes
match and changed-file checks pass. The original27 interruption journeys pass
27/27 and original six long-hold/continuation cases remain6/6. Those two runs
precede the final finite-opening-gap guard; the guard is directly tested and the
new four journeys and full54-case cohort are repeated on the final source.
The already evaluated seed2026101304 cohort repeats53/54; all54 independently
reconstructed verdicts match. It is a retrospective regression replay, not a
new prospective cohort. The same ambiguous-neighbor return remains failed.

## Live assistant integration requirements

The current assistant loop expects controller destination, lift statistics,
notifications and verified steps, and dispatches task changes through its existing
tool-controller types. CameraDelivery is not a drop-in replacement. Next build
an opt-in adapter that keeps camera/proprioception as action inputs, supplies a
separate physics evaluator, preserves rack/held-tool context across task changes,
and checks cancellation epochs before queued motion. Keep default interaction
working while measuring complete natural retrieval/return/change, conversation
and Stop/resume journeys through the actual application.

## Reproduction

From the existing workbench WSL environment with the preserved local fixture:

```sh
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_grip_recovery_interruptions.py runs/new-grip-interrupt
```

Protocol `fixtures/camera_grip_interrupt_protocol.json` SHA256:
ba20a973402bea72c9b66a452f3ff6715e2b614422e2495ba229040970d1332b.
The script checks the original cached fixture SHA before replay. Output path must
be new. Raw generated layouts/traces stay local; this verifies one known loss
context, not arbitrary unseen recovery or wall-clock acoustic Stop latency.
Rollback: disable phase_recovery/recover_grip, or revert the specific resume
route. No microphone, external model call or hardware action occurred.
