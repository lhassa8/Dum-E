# Carrying limiter rejected; scene-cache race repaired — October 14, 2026

The frozen motion limiter does not qualify for the assistant. Recorded replay
passes fall from 4/10 to 0/10. A complete fresh pi0.5-LIBERO cohort passes the
combined grasp, Stop hold, fresh resume and native-goal gate in 2/6 baseline
episodes and 0/6 candidate episodes. Keep the experimental limiter disabled.
The useful implementation change is a scene-generation guard preventing an old
physics step from publishing observations after a new layout has been requested.
Aggregate evidence and raw report hashes are in [the evidence JSON](carry-governor-evidence.json).

## Frozen hypothesis and judge

Previous torque allocation improved known replay holds from 4/10 to 6/10 but
left physical failures and a 10.7 ms callback outlier. This experiment changes
strategy: reduce carrying commands before Stop instead of increasing braking
gains or actuator limits. Freeze a 10 mrad modeled displacement budget and 50%
directional torque reserve. No tuning after either cohort's failures.

The limiter sees the native decoded six-axis OSC delta, arm Jacobian, mass
matrix, bias, torque bounds and control frequency. It computes a minimum-norm
joint velocity proposal, then a scalar command reduction using ideal joint-hold
response and estimated torque-limited braking distance. The seventh policy input
remains the unchanged gripper command. There is no object-state input. Independent
simulator truth supplies the evaluator's grasp/lift trigger and physical scores.

This is a heuristic, not a stopping-distance guarantee: commanded displacement
is treated as motion over one 50 ms step; changing dynamics, contact forces and
ongoing orientation goals are omitted. Measured velocity is logged but does not
drive this version's estimate. Native robot clipping remains authoritative at
±80 N·m on joints 1–5 and ±12 N·m on joints 6–7. Joint holding stays kp300,
damping ratio2. Protected physical criteria remain bilateral native pad grasp,
80 mm minimum lift, 10 mm translation, 20 mrad joint range and more than one
simulated second of holding. No hidden weld, teleport or pose freeze is used.

## Recorded replay

All ten qualified Stop windows from `fresh-alignment-001` are replayed once per
profile. Its two no-trigger episodes remain failures in that source's twelve-case
denominator; they are not converted into holding passes. The baseline's dense
metrics match the prior torque-allocation baseline exactly. All twenty trials
complete without errors; their unchanged trajectory prefixes match within 1e-6.

The candidate activates only for positive grip during the last 200 simulated
milliseconds before the recorded Stop. This onset uses known future Stop time
and is an offline diagnostic, not deployable behavior. Each variant captures
its own measured joint goal at the same recorded callback time.

Although every candidate retains pad grasp and substantially reduces joint
excursion, all ten fail the original minimum-lift criterion at the fixed Stop
time. For example, task0/seed101 baseline minimum lift is 86.90 mm and joint range
12.71 mrad; the candidate is 65.49 mm and 2.83 mrad. Better holding motion does
not compensate for failure to reach the required height. An independent raw
audit recalculates every physical score, checks the unchanged baseline, and
reconstructs forty limiter decisions from recorded matrices and commands.

## Fresh checkpoint cohort

Run all three frozen LIBERO spatial tasks with policy seeds303/404, baseline
and candidate, twelve episodes total. Simulator seed7 and initial state0 remain
fixed. Real CUDA pi0.5 inference supplies five actions per replan. The candidate
now activates on every positive grip while running, without any future Stop
input. This activation differs from replay and includes grasp closure.
The evaluator requests Stop only after native grasp and 80 mm lift. Resume
discards pending work, rejects stale-generation actions and requests a fresh
camera/proprioception observation. Original220 active steps include inference
waits. Sequential wall-time physics and inference waits prevent exact causal
pairing despite the same explicit policy seed/draw schedule.

| Profile | Attempted | Qualified Stop | Hold passes | Native goals | Combined passes |
|---|---:|---:|---:|---:|---:|
| Baseline | 6 | 5 | 3 | 5 | 2 |
| Carrying limiter | 6 | 4 | 4 | 0 | 0 |

Every candidate ends at the original220-step limit. Four reach a stable qualified
hold, but none finishes placement. The candidate's median command scalar is
0.0975 across918 decisions. It reduces commanded motion too much for this task
budget. Baseline failures include two grasp/hold losses, one unsuccessful native
goal and one native-goal episode with no qualified lifted Stop. These are counted
as failures; no result is selected away or used to retune this cohort.

The independent audit verifies all twelve planned identities, as-run source
hashes, terminal budgets, fresh resumed submissions and every holding sample.
Dense native samples cover the entire original hold windows at 2 ms intervals;
polling samples are also included. All repaired-run scene identifiers match.
The final candidate render was inspected: it is still holding the bowl rather
than having completed placement. Rendered appearance does not replace the judges.

Actual375 warmed policy client calls have median111.68 ms, sample p95127.68 ms
and maximum295.81 ms, excluding preprocessing, speech and motion. Checkpoint
load is17.792 s and warmup11.071 s. Metadata records JAX0.5.3, cuda:0, OpenPi
`215abfb217dbac7d5f1273282331b9b1866c0479` and checkpoint object-manifest SHA256
`450f2d7b90db37ff3db84074fd9a67ba49fba05c1c482c430b1d1c5de8772084`.
The added limiter computation has median0.152 ms, p950.261 ms and maximum0.544 ms.
These are added computation times, not whole-controller deadlines. Other desktop
GPU applications were active. No voice-latency or real-hardware claim follows.

## Retained incomplete attempt and scene repair

The first fresh attempt retains seven attempted episodes and five not run. Its
seventh hold starts with an old scene at simulated time12.55 s and ends with the
new scene at1.496 s, causing the hold-stall assertion. That cohort is contaminated
by scene-cache publication and is not clean comparative evidence, even where
earlier episodes appeared valid. Preserve it under `fresh-carry-governor-001`.

An already-running old `env.step` could republish its observation after HTTP
initialize cleared the cache. The repair distinguishes requested scene generation
from command generation, tags native callback observations, and checks scene
identity both after stepping and before publishing encoded images/NPZ/judges.
Stop/resume may change command generation within the same valid scene.
The controlled regression runs the archived and current Runtime classes with
initialize interleaved into old-step completion: old cache leakage occurs only
in the archived version. This is a simulated concurrency regression, not a
physical-control score. Separate real neutral-reset probes observe no stale
Ready samples either before (847 polls) or after (836 polls); they did not
naturally reproduce the intermittent race.

The repaired second attempt repeats the same frozen limiter parameters and
policy seeds, completes all twelve episodes, and supplies the comparison above.
Eleven existing policy-coordinator regressions, changed-helper Ruff checks and
all46 protected upstream byte checks pass. Initial regression invocations lacked
the two integration source paths; the corrected command below passes without
installing or changing dependencies.

## Runtime restoration and reproduction

Only the verified experiment policy/simulator processes were stopped. Public
8996 remains Ready. Gemma was temporarily unloaded for CUDA policy memory and
restored from the cached local Q4_K_M model: context4096, one slot, requested
maximum GPU offload, no TTL, null remote-device identifier. Bonsai remains local
with the same context/slot/residency settings. A fresh read-only `/interact`
camera question identifies all three tools in1.362 s; the arm's epoch stays0.
No microphone or hardware was activated. An earlier restricted LM Studio probe
could not reach the service; the unrestricted check confirmed it was running.

From the extension, with the existing environments and retained raw data:

```sh
.venv-linux/bin/python scripts/audit_libero_carry_replay.py runs/policy-runtime/carry-governor-001 --source-run runs/policy-runtime/fresh-alignment-001 --reference runs/policy-runtime/torque-allocation-001/report.json
.venv-linux/bin/python scripts/audit_libero_carry_fresh.py runs/policy-runtime/fresh-carry-governor-002 --physics runs/policy-runtime/carry-governor-physics-002
.venv-linux/bin/python scripts/check_libero_scene_generation.py --before runs/policy-runtime/fresh-carry-governor-001/libero_runtime.py
PYTHONPATH=integrations/openpi-client/src:runs/policy-runtime/openpi/packages/openpi-client/src .venv-linux/bin/pytest -q integrations/openpi-client/tests/test_libero_coordinator.py
```

New live experiments require both `serve_local_pi05.py --paired-experiment` and
`libero_runtime.py --carry-governor-experiment`, using the existing pinned
checkpoint/configuration, then `verify_libero_carry_governor.py NEW_OUTPUT
--openpi runs/policy-runtime/openpi`. Choose new output directories; no helper
overwrites a live run. Raw traces, snapshots and renders remain local under
`runs/policy-runtime/`. The next hypothesis should use measured velocity and
distinguish grasp closure from transport; do not raise the220-step budget or tune
these failed cases into passing evidence. Original2/3 pretrained voice
qualification and the public workbench controller remain separate observations.
