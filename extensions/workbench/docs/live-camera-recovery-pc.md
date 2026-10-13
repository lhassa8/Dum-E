# Camera recovery and continued-session repair on the PC

October 13, 2026. Baseline d975557 introduced the opt-in camera interface, but
its third continued-session sequence failed during a resumed screwdriver carry.
This candidate improves that experimental profile; the main assistant and
original physics/placement thresholds remain unchanged.

## What the failed traces established

The frozen diagnostic uses the already evaluated wrench-loss case025 plus three
delivery/Stop/resume/return cycles for screwdriver and wrench, without resetting
between a tool's cycles. Baseline completed ten legs and failed two; the last
wrench return was not reached. Both failures stopped at "Observing supported
tool after grip loss". The gripper was closed with an approximately empty gap
of 0.000000017m, and the original one-attempt recovery had already braked.
The asynchronous detector wait nevertheless demanded a held-handle gap there.
This contradicted the recovery sequence's deliberate empty-hand confirmation.

The repair recognizes only that owned observation phase and requires finite,
closed-command gaps in [0,15mm) before and after each physics tick. The carrying
uncertainty remains until a fresh supported-tabletop camera observation arrives.
The ordinary carry gate, 2mm free-space shrink trigger, one-attempt recovery
budget and camera confidence/freshness requirements remain intact. The known
loss then reacquired and returned physically; continued wrench use still exposed
a separate geometric refusal after a real dropped tool.

An attempted closed-hand retreat/resurvey exposed that wrench but did not restore
a valid geometric fit. It added motion without completing the failed leg. That
prototype was rolled back and is absent from the shipped actor. Raw failed
images and traces remain local; no fit was trained or uncertainty gate relaxed.

## Removing duplicate work and controlling the carry path

Profiling a stale hammer-return frame pair showed repeated full-image depth and
color preparation in the detector's independent fallback fits. The preparation
is now shared within one frame only. All 48 existing frozen optical cases and
both recorded hammer frames produce exactly equal output dictionaries, including
fit scores, positions, ambiguity and direction cues. Five interleaved trials per
frame compare old and new code without using labels or fitting a model. The two
hammer frames' median CPU times changed from 154.11/247.38ms to 66.89/118.32ms.
These are paired diagnostic timings, not live-microphone or GPU-contention claims.

The optional camera profile now plans transport and descent in Cartesian
position with smooth shortest-arc wrist rotation, extending its existing linear
lift planning. Original joint continuity, IK residuals and refinement limits
remain: 0.075rad between waypoints, unchanged solver tolerances, sampling at
1/2/4 times the original count and an additional-refinement cap of 400 points.
The actor still checks measured pose and grip during execution. This changes
path geometry and wrist motion together; the evidence does not isolate a pure
speed or wrist-only causal effect.

Some kinematic plans took over 200ms. They now run using separate kinematic data
and a captured robot reading while the owner advances real simulation physics
under the original gravity hold. The worker never writes live state. Epoch
cancellation discards results; planning snapshots older than 250ms and a first
waypoint exceeding the measured 0.075rad continuity limit refuse motion.
The alternate scene detector also uses this cooperative computation path.
Outcome logs retain actor/robot-plan evidence, separate from evaluator-only truth.

## Measured complete journeys

- Final frozen diagnostic: 13/13 physical legs, including known-loss reacquisition
  and three continued cycles per tool. An external observer intercepts every
  actual physics tick, including computation waits, and independently measures
  lift/unrelated-tool drift. It applies the original 35mm placement, 80mm lift,
  rest-height/speed and open-hand checks. All thirteen independent verdicts match
  successful outcomes. This is a known diagnostic replay, not a prospective rate.
- Three complete interface sequences in one continued session: screwdriver
  delivery with conversation during transport, Stop/resume, verified screwdriver
  return before wrench delivery, then contextual wrench return. All twelve
  placements passed; HTTP request to observed stopped-state times were
  63.64, 112.00 and 24.62ms. n=3, excludes speech and acoustic settling; no tail
  reliability claim. Descriptive median63.64ms, linearly interpolated p95107.16ms,
  zero failures. Raw evidence includes the previous continued-session failure.
- Saved Windows synthetic speech: "Could you bring me something for turning
  screws, please?" → CUDA small.en transcription → actual Bonsai interpretation
  → original task/MCP bus → camera pickup/delivery/return. Exact transcription;
  delivery error 7.52mm, observed lift 201.95mm, verified return error 9.55mm.
  ASR HTTP 315.55ms (decode 109ms, model 185ms); native interpretation 507.49ms,
  decision 538.71ms, pickup-phase 2626.18ms, completion 18579.03ms from request
  receipt. n=1 warm sample, no concurrent benchmark. These clocks exclude live
  utterance completion and audible onset. ASR plus decision already exceeds
  the provisional 0.5s substantive-acknowledgment target; no timing boundary or
  target has been redefined. Common-decision/final-word and spoken-Stop targets
  still require complete measured boundary data and distributions.
- 315 full regressions, lint and all 46 protected upstream byte hashes pass.
  Safety tests cover late/stale plans, continued physics, unchanged optical
  uncertainty, empty-recovery ownership and independent full-pose continuity.

## Reproduction and remaining work

Use the existing Windows launcher with `-CameraTools`; browser 8886, simulator
8885, MCP 8802. Listening starts off. The unchanged main assistant remains on
8876. Omitting the switch is the rollback to the main profile. From the
extension's WSL directory, with already loaded language/vision models:

```bash
MUJOCO_GL=egl .venv-linux/bin/python scripts/verify_live_camera_recovery.py runs/new-camera-recovery
.venv-linux/bin/python scripts/verify_live_camera_interface.py runs/new-camera-interface
.venv-linux/bin/python scripts/verify_voice_delivery.py --url http://127.0.0.1:8886 --audio runs/camera-live-recovery-001/natural-fetch-sapi.wav --audio-source 'Windows synthetic speech' --message 'Could you bring me something for turning screws, please?' --expect-model-interpretation --return-after-delivery --output runs/new-camera-voice
```

Each evidence directory must be new. The voice command uses the local recorded
synthetic fixture from this workstation. `--audio` supports Windows/WSL without
depending on the historical Mac `say` executable. A sandboxed synthesis attempt
stalled with a zero-byte file; its owned process was stopped. Generation through
the already installed host speech engine succeeded; no recognition device fallback.

The new full-pose profile still needs a frozen prospective varied-layout cohort
through its actual camera adapter. Previous 53/54 belongs to an earlier offline
candidate. Stop during an active perception/planning call can close the generator;
held-task resume currently refuses and retains context for a fresh destination
plan. Ordinary transport Stop/resume passes, but broad all-boundary recovery is
not established. Live camera-mode microphone/echo/audible timing and a convincing
user demonstration remain outstanding. This milestone is progress toward the
full goal, which stays active. No raw recordings/data uploads, new model fits,
paid requests or hardware actions.
