# First action-head adaptation trained; physical validation pending

A head-only OpenVLA-OFT pilot now has actual trained checkpoints. The existing
pretrained visual/language backbone and proprioception projector remain frozen;
only the existing151,117,831-parameter action head is updated. No adapted policy
has been deployed, physically validated or promoted to the public assistant.
The [prospective training protocol](action-head-adaptation-protocol.json) fixes
supervision, optimizer, saved steps and subsequent physical evaluation split.

## Interrupted demonstrations

The same six published-action cases are replayed with a pause at their first
completed source step showing bilateral pad contact and80mm lift. Original
joint holding uses kp300/damping2, at least2wall seconds and more than1sim second,
80mm minimum lift,10mm translation and20mrad joint range. Hold time is explicitly
excluded from the220active-step budget; source/settling actions remain counted.
Resume applies the next recorded action with newly recorded pre-action images.
It is not fresh learned-policy inference, a stale-action API test or spoken Stop.

| Task/demo | Hold | Released placement after resume | Combined |
|---|---|---|---|
|0/0|Pass|Pass|Pass|
|0/1|Pass|Pass|Pass|
|1/0|Pass|Pass|Pass|
|1/1|Fail: bilateral contact briefly lost|Pass|Fail|
|2/0|Pass|Fail: gripper contact remains|Fail|
|2/1|Pass|Pass|Pass|

Independent auditing recomputes dense2ms hold and final placement gates, verifies
all source actions against HDF5 and inserts actual hold frames in the video
timeline without duplicate resume frames. Five holds pass; four complete journeys
pass. Each hold contains547samples and1.05sim seconds. Altering one hold contact,
joint-range or lift witness is rejected in three independent negative checks.
No physical thresholds are relaxed. Recorded-state fidelity remains unqualified;
the inserted pause also changes reference time, so that metric cannot establish
exact paused replay. Raw frames/actions/contact traces/videos remain local.

## Supervision and frozen features

Only the four complete journeys across all three tasks supply training data.
Their541active actions produce485unpadded8×7windows, excluding all windows
crossing the pause. Both failed journeys are explicitly listed and excluded.
Every label independently matches the recorded native OSC action. Inputs are
actual native pre-action front/wrist RGB, robot proprioception and the task
prompt. Stored publisher post-action images, evaluator truth and episode IDs
are not actor inputs. Four episodes are not485independent examples; no random
window split is used for model selection.

Verified original checkpoint revision6d0231af0e48c5985f1ff86908f4674b84bc049b
executes485actual CUDA forward passes on the RTX5090. Frozen feature shape is
1×56×4096 in BF16. Every cached feature reproduces the original head's native
action output exactly. Feature extraction takes111.307ms median/121.522ms sample
p95 across485calls, maximum1230.698ms including cold first work. This includes
the extra head reconstruction check; it is not whole-assistant response latency.
Checkpoint loading takes71.978seconds, separate from those calls. Gemma is idle
and temporarily unloaded during extraction/training; Bonsai stays resident.

## Explicit label-normalization change

Original quantile clipping alters some expert labels: maximum native X input
change0.192027 corresponds to9.601mm of commanded translation. The unchanged
action head and publisher decoder accept values outside normalized[-1,1].
For this adaptation only, labels use the original affineQ01/Q99 transformation
without clipping. Original gripper conversion and decoder remain unchanged;
native controller bounds and physical judges remain unchanged. This deliberately
differs from publisher pretraining label clipping. The default normalization
tool retains its old clipping mode; `--affine-only` selects this pilot mode.
All485chunks are reconstructed through the actual original publisher decoder
within1e-6 before training. Unmodified raw labels and both normalized variants
remain local. There is no guarantee this normalization change improves control.

## Actual training result

The pretrained head identity is rehashed before loading. Training uses FP32 master
weights/AdamW state and BF16 CUDA autocast, seed7, batch8, learning rate1e-5,
weight decay1e-4, gradient norm clipping1 and exactly200updates. No backbone or
projector gradients are computed; training reads cached frozen features.

| Saved step | Training L1 |
|---|---:|
|0|0.124160|
|50|0.119340|
|200|0.108766|

The200-step run completes in26.670seconds including full training-set evaluations
and local checkpoint saves. All gradients/losses are finite. This is a modest
fit improvement on four known demonstrations, not validation performance.
An independent weight audit confirms step0 exactly matches the original at
BF16 precision;34,268,899parameter values differ at step200, all finite.
Checkpoints remain under `runs/grasp-adaptation/action-head-pilot-001/` and are
not committed. Their hashes and aggregate results are in
[the evidence](action-head-pilot-evidence.json); raw training traces/features stay local.

Next compare the original, step50 and step200 heads using benchmark tasks0/1/2
and initialstates5/6 with original complete physical gates. Select only using
that validation, then compare original/selected heads on untouched states7/8.
No state0 or validation/final observation is used as training supervision.
Demonstration numbers are separate from benchmark initial-state numbers; the
earlier fingerprint inspection scopes scene overlap. Base pretraining already
uses LIBERO, so this is not a claim of novel tasks or broad generalization.

## Workbench restored

Both GPU experiment processes finish. Local Gemma is restored explicitly from
the local entry in the duplicate-key menu, context4096, one slot, no TTL;
LM Studio reports deviceIdentifier=null for Gemma and Bonsai. A read-only camera
question identifies screwdriver/wrench/hammer in1477.4ms, returns answer mode
with no task ID, and leaves the assistant Ready/not busy at epoch0. This is one
restoration probe, not a new broad latency qualification. No microphone or real
robot hardware is activated. The larger goal remains active.
