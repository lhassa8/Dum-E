# Head-only pilot earns no replacement: all three heads score four of six

The complete18-episode comparison and both independent audits pass accounting
and provenance checks. Original, step50 and step200 each pass4/6complete
interrupted physical journeys. The predeclared tie rule retains the original.
No adapted head is promoted, and benchmark states7/8 remain unused for training
or policy rollouts. Lower training loss did not improve this validation score.

| Head | Training L1 | Complete validation journeys | Released placement |
|---|---:|---:|---:|
|Original|0.124160|4/6|6/6|
|Step50|0.119340|4/6|6/6|
|Step200|0.108766|4/6|6/6|

This rejects this specific four-demonstration head-only pilot as a replacement.
It does not establish that adaptation cannot help or identify whether data,
frozen features or the loss objective caused the limitation. More steps on
the same four examples are not justified by the lower loss alone.

## A useful integration finding: native goal precedes release

In18/18exact evaluated trajectories, the first native task-success signal occurs
while the gripper still contacts the bowl. The old native-goal-only termination
would finish before physical release. The explicit evaluation mode now continues
until actual released placement or the same220active-step budget expires.
All three policies then complete released placement in6/6cases each.

This is a stronger completion check in the experimental runtime, not an adapted
model achievement. Enable `--require-released-placement` for full physical
evaluation. The legacy default is preserved for reproduction of earlier native
goal experiments. The public workbench controller is unchanged.

## Frozen comparison and actual outcomes

The [prospective protocol](action-head-validation-protocol.json) fixes tasks0/1/2,
initialstates5/6, original/step50/step200, seed7,8action replanning with bounded
5+3submissions and220active steps including inference waits. Explicit pauses are
excluded. Same-state comparisons use the same runtime/controller and released
placement gates. The simulator is restarted between the two state batches;
all three GPU heads remain loaded, frozen and individually warmed throughout.

| Validation case | Original | Step50 | Step200 |
|---|---|---|---|
|State5/task0|Hold loses bilateral contact|No observed Stop trigger|No observed Stop trigger|
|State5/task1|Pass|Pass|Pass|
|State5/task2|Pass|Pass|No observed Stop trigger|
|State6/task0|Pass|Pass|Pass|
|State6/task1|No observed Stop trigger|No observed Stop trigger|Pass|
|State6/task2|Pass|Pass|Pass|

An eligible trigger requires observed native bilateral pad contact and80mm
lift. The one failed hold stays above93mm and within translation/joint limits,
but loses contact; it remains a failure. No-trigger cases count as full-journey
failures despite successful placement. A missing observed trigger does not prove
there was never a fleeting eligible native contact between evaluator polls.
Step200 trades one success for another; it has no net score advantage.

Original hold limits remain80mm lift,10mm translation,20mrad joint range,
continuous bilateral contact, kp300/damping2, at least2wall seconds and more
than1sim second. Placement requires native success, plate support, zero gripper
contact and stable final0.5sim seconds, within35mm XY and5mm movement. No gates,
budgets or candidate parameters are retuned after outcomes. A pre-step guard
also prevents step221 if a pause ends at the active budget boundary.

## Audit, timing and recording scope

Both9case audits verify as-run actor/runtime hashes and scene generations,
all286real GPU responses, immutable requested-head SHA identity, dense holds,
physical release witnesses, fresh post-resume inference and all2148selected
native policy action vectors against accepted prediction packets. Stop can
interrupt a selected action's torque execution; vector identity is not a claim
that every selected target finishes after cancellation. Old local chunks and
pending predictions are discarded, and stale submission probes return409 while
paused. Native running-generation rejection is additionally isolated in a unit
test. A separate live neutral-action smoke on training state1 resumes from
epoch1 to3, rejects epoch1 with409 while running, and accepts a current-epoch
neutral packet. It is infrastructure evidence, not an extra learned-policy
success. The current collector adds that post-resume probe for future cohorts.

Client round-trip inference timing across286calls is112.324ms median,
203.678ms sample p95 and325.045ms maximum. It excludes speech, checkpoint loading
and physical motion. Original/step50/step200 warmup calls take1106.9/109.7/107.1ms;
model/head loading takes78.825seconds, outside episode budgets. Other desktop
GPU activity is not isolated. Six task/state cases are a small validation set
on known LIBERO tasks, not broad generalization or real-hardware readiness.

The captured native JPEG frames and wall timestamps produce local variable-frame
videos of actual GPU-controlled rollouts. Two terminal renders were inspected.
The as-run collector did not capture fresh frames inside its explicit hold loop,
so videos bridge those intervals with the last available frame. Dense2ms native
records are the holding evidence; the video alone cannot establish hold motion.
This recording gap is repaired in the current collector for future runs and
smoked with an actual recorded frame. Completed recordings/scores are preserved;
no rendered or human-action replay is presented as fresh policy inference.

Nine focused tests cover release/contact/goal/window/placement/movement limits,
the220step resume boundary and running-epoch rejection. All46original upstream
files remain byte-identical. Raw traces, videos, predictions and trained weights
remain local. [Aggregate evidence](action-head-validation-evidence.json) contains
all case outcomes and audit summaries; selection is deterministic and does not
read training loss. No incomplete cohort is promoted.

## Next action and restored workbench

Retain the original policy. Broaden independently qualified demonstration
coverage before further adaptation, rather than tuning offsets or thresholds
against these validation failures. Evaluate any revised supervision/representation
hypothesis prospectively; preserve final states7/8 for a candidate that earns
replacement on validation. Dependable learned grasp/Stop/resume, broader camera
assistance and the human live voice demonstration remain parts of the full goal.

Both private simulators and the GPU validation service exit cleanly. Local
Gemma is restored alongside Bonsai, context4096/one slot/noTTL and no remote
device. A read-only camera question sees all three tools in1469.6ms and leaves
the public assistant Ready/not busy at epoch0, with no motion task. This one
probe does not establish broad latency qualification. No microphone or hardware
is activated. The overall goal remains active.
