# Fresh-policy alignment comparison — PC, 2026-10-13

Reject the online +3 mm world-X correction. All 12 real-policy episodes reach
native placement success, but the combined grasp/hold/fresh-resume gate passes
only 4/6 baselines and 1/6 corrected episodes. The original saved-voice
qualification remains **2/3**; no adapter or controller is promoted.

## Scope and fixed comparison

The [earlier replay](libero-grasp-alignment-pc.md) established alignment
sensitivity on one recorded episode. This prospective development experiment
uses actual pi0.5-LIBERO checkpoint inference with new camera/proprioception
observations after every replan and after interruption. Test all three supported
LIBERO spatial tasks, simulator seed7/state0, policy seeds101/202, baseline then
candidate: 12 episodes, no omitted failures or repeat cohort.

The online candidate changes one OSC translation input by +0.06 (+3 mm world X)
on the first positive closing command. The preceding open command used by the
replay is no longer available when that online command arrives. This timing
difference means it is a new candidate, not an exact reproduction of the replay
intervention. The actor uses action/proprioception/image inputs; evaluator-only
object state triggers and measures Stop but does not choose the correction.

The separate policy server requires explicit seed/draw fields when started with
`--paired-experiment`. Each inference sets `fold_in(key(seed), draw)` before the
pinned native Policy.infer split. Draw index continues across Stop/resume.
Repeated identical observations and seed/draw keys produce exactly identical
checkpoint actions. This is an opt-in experiment endpoint; the normal server
and public coordinator retain their existing interfaces and RNG behavior.

Pairs share an RNG schedule, but continuously stepping physics and wall-time
inference waits can produce different observations before intervention.
This experiment assesses observed qualification, not an isolated causal effect
of the offset. Encoded NPZ hashes identify archives, not semantic equality of
their array contents. These six fixed task/seed pairs are not a broad held-out
workshop generalization cohort.

## Retained results

| Task / policy seed | Baseline | Online correction |
| --- | --- | --- |
| Between plate and ramekin /101 | Pass | No qualified grasp trigger |
| Between plate and ramekin /202 | Pass | Joint range21.093mrad >20mrad |
| Next to ramekin /101 | Pass | Pass |
| Next to ramekin /202 | No qualified grasp trigger | Grip contact loss; motion13.494mm >10mm |
| Table center /101 | Joint range30.451mrad >20mrad | Joint range24.289mrad >20mrad |
| Table center /202 | Pass | Joint range21.251mrad >20mrad |

All ten episodes that reach the trigger perform native Stop/hold/resume and
request fresh inference afterward. Old action generations are rejected after
Stop, and pending inference results are discarded. Holding uses unchanged native
JointPositionController kp300/damping ratio2 and original torque clipping.
The original 80mm pad-contact lift, 10mm translation, 0.02rad joint range,
two wall seconds, >1sim second, five-second stall and 220active-step limits remain.
Contact retention and holding metrics use captured native sensor snapshots;
they do not prove every unrecorded torque-cycle contact. This is an HTTP
interruption experiment, not spoken Stop or human microphone qualification.

Native goal success also does not establish a released, resting workshop tool:
terminal gripper commands are still positive. These bowl tasks remain separate
from the workbench's full delivery/return journeys and 35mm placement judge.

Across268 warmed checkpoint websocket requests, median/p95/max are
130.79/217.99/353.49ms. Timing starts after observation preprocessing and excludes
speech and physical settling. GPU load takes26.021s; discarded warmup15.885s.
The real pinned JAX0.5.3 checkpoint runs on CUDA without CPU fallback. Gemma was
temporarily unloaded (23,391MiB GPU memory free before policy loading); Bonsai
and existing ASR/services remained resident. Gemma was restored with its local
Q4_K_M model, 4096context, one slot and3600s TTL. Owned8900/8901 services were
closed; existing8896/8996 services were preserved.

## Reproduction

Use the existing isolated environments from the workbench directory in WSL.
Keep8900/8901 free and temporarily unload local Gemma with `lms unload
workbench-vision-gemma` in Windows. Run the two services in separate terminals,
then the evaluator in a third; use new output directories for every run:

```bash
/home/user/.local/share/dume/policy-215abfb/bin/python scripts/serve_local_pi05.py \
  --paired-experiment --openpi runs/policy-runtime/openpi \
  --checkpoint runs/policy-runtime/pi05_libero \
  --warmup runs/policy-runtime/warmup-001.npz \
  --output runs/policy-runtime/fresh-alignment-server-NEW --port 8900

/home/user/.local/share/dume/libero-py38/bin/python scripts/libero_runtime.py \
  --openpi runs/policy-runtime/openpi \
  --config-dir runs/policy-runtime/libero-render-001/config \
  --output runs/policy-runtime/fresh-alignment-physics-NEW --port 8901

/home/user/.local/share/dume/libero-py38/bin/python scripts/verify_libero_fresh_alignment.py \
  runs/policy-runtime/fresh-alignment-NEW --openpi runs/policy-runtime/openpi
```

Wait for actual policy warmup and both service-ready messages before the third
command. After evaluation, Ctrl+C only those two owned service terminals, then
restore Gemma in Windows with `lms load google/gemma-4-31b --identifier
workbench-vision-gemma --gpu max --context-length 4096 --parallel 1 --ttl 3600 --yes`.
The existing interactive policy launcher uses8896, now occupied by the preserved
Mink demo; it is not the launcher for this separate experiment.

Raw data: `runs/policy-runtime/fresh-alignment-001`,
`fresh-alignment-physics-001`, `fresh-alignment-server-001` and
`check-paired-policy.json`. [Curated evidence](libero-fresh-alignment-evidence.json)
includes all outcomes, checkpoint identity, protocol, timings and raw hashes.
An independent audit recalculates hold metrics, verifies every submitted action
against checkpoint output, checks the single allowed correction, confirms native
success in physics logs, and verifies fresh inference after each resume.
Lint and all46 preserved upstream bytes pass. No microphone was activated.

Next: change the hypothesis from a universal approach offset to physical braking
and grasp-aware recovery. The failed baseline table-center hold enters braking
with joint6 velocity about-0.959rad/s; its captured native brake begins2.38ms after
Stop. These values motivate a bounded pause-controller experiment with unchanged
torque caps and contact judges, followed by a separate prospective fresh-policy
cohort. Known failed windows are development data, not held-out validation.
