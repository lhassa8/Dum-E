# Live pretrained-policy voice experiment on the PC

2026-10-12. Baseline: `e8e116d`, Windows 11 / local WSL2 Ubuntu / RTX 5090.
This is a separate simulated Panda lab, never a Dum-E hardware controller.
The workbench's tool controller, tool_contacts_v2, shared gravity hold,
35 mm placement and 80 mm lift gates are unchanged.

Actual official pi0.5-LIBERO now runs through the existing cancellable OpenPi
client, local Bonsai task selection and the workbench's local CUDA ASR. The
browser reuses the existing local speech, microphone and Silero modules. The
microphone starts off; no human microphone recording was performed.

**The frozen live smoke qualification is 2/3, so this remains experimental.**
The earlier standalone policy test was 3/3 native simulator successes. Native
placement success and this stricter voice/physical interruption qualification
are different results. Neither establishes workshop generalization or hardware
readiness. The complete project goal remains active.

## Frozen evaluation

Protocol: `integrations/openpi-client/fixtures/libero-live-pc-smoke.json`, SHA256
`c7b5e6155ccec8823c9a75b8c9a1cfce7e54d4ec183e39321aa259a50961f26b`.
Spatial tasks 0/1/2, initial state 0, simulator seed 7, replan every five actions.
The original 220-step limit counts active physics steps, including inference
waiting. Explicit paused steps are excluded; resume never resets the budget or
scene. Both simulated cameras and measured robot proprioception feed the policy.
Object truth is available only through separate evaluator endpoints.

The server has a continuous policy RNG stream across episodes and development
trials. One actual saved observation warms the GPU before readiness, consuming
one RNG draw; its ten predictions are discarded without actuation. RNG is never
reset on Stop/resume. This is not a paired deterministic controller comparison.

The sequence is saved synthetic task speech, local model selection, real policy
motion, an early conversation, an 80 mm two-finger-contact lift trigger, saved
Stop speech, continued gravity-loaded holding, rejection of an old-generation
action, and resume from new camera observations to the original native success
predicate. Hold gates remain contacts throughout, lift >=80 mm, drift <10 mm,
joint excursion <0.02 rad, >=2 wall seconds and >1 simulated second. Sampling
continues until both clock requirements are met, with a five-second stall limit.

| Task | Complete sequence | Hold drift | Joint excursion | Minimum held lift | Resume |
| --- | --- | --- | --- | --- | --- |
| 0: between plate/ramekin | FAIL | Not reached | Not reached | Not qualified | Not tested |
| 1: next to ramekin | PASS | 0.661 mm | 0.00358 rad | 97.3 mm | Native success |
| 2: table center | PASS | 1.432 mm | 0.01639 rad | 87.9 mm | Native success |

Task 0 reached native placement success, but no observed >=80 mm lift coincided
with the native two-finger contact predicate. Maximum observed lift was 119.4 mm;
maximum lift with that contact predicate was 7.7 mm. It is counted as a failed
interruption qualification, never replaced or removed from the denominator.
The delivered objects' release was not qualified: native success was reached
with the positive grip command still present.

Tasks 1/2 advanced 1.036/1.012 simulated seconds over 2.342/2.374 wall seconds.
The Stop-origin sensor snapshots were 0.408/0.568 ms old. Saved Stop clips
available to cancellation response took 235.3/227.9 ms; direct cancellation
calls took 1.51/2.20 ms. These are two samples, not a tail-latency guarantee, and
exclude microphone capture, pause detection and audible response onset. The
task-2 trace also rejected a real late inference chunk after Stop. Both
qualifying episodes independently rejected a deliberately submitted stale
epoch. They finished in 114/90 policy actions and 157/122 active physics steps.

Curated evidence: `libero-live-pc-evidence.json`. Raw audio, actions, traces,
weights, logs, camera videos and screenshots remain local under ignored `runs/`.
The fixed run IDs are `live-voice-012`, `live-voice-013`, `live-voice-014`.

## Execution and failure history

Hypothesis: invalidate physics first, then cancel client generations, preserve
the last grip command under real gravity, and replan on resume. The judge and
rollback decision were fixed before each meaningful experiment. Failed trials
remain local; no hold gate was reduced.

- Native zero-delta OSC and captured OSC goal/nullspace replay holds failed
  drift/joint gates. After two similar failures, the strategy changed to a
  native joint torque servo during pauses.
- A measured-velocity damping replay passed, but live motions failed. Stronger
  damping also altered the policy approach when applied during inference gaps.
  Those versions were rejected. Native OSC now handles inference gaps; the joint
  servo operates only during explicit pauses.
- Fixed stiffness 300 and damping ratios 1/2 were tested within the native joint
  controller's limits, without changing robot torque caps. Initial live tests
  still failed. Trace inspection showed that Stop also needed to be observed
  inside a running `env.step`, rather than after its whole 50 ms control interval.
- The native torque callback now checks paused state each physics substep,
  captures the measured robot joints and uses JointPositionController torques.
  The original OSC bookkeeping still runs; all policy vectors retain their
  original OSC meaning. Seven policy outputs are never interpreted as joints.
- Evaluator snapshots formerly updated only at rendered/control ticks. They
  could include movement before Stop in the measured hold interval. Sensors now
  refresh on native torque callbacks and completed steps; `/stop-judge` captures
  the last sensor snapshot when Stop is accepted. The new protocol measures from
  that snapshot and records its age. Earlier trials remain unqualified.
- A separate typed-policy gravity witness (`release-witness-001`) passed:
  opening the fingers during an >=80 mm lifted pause caused an **80.70 mm drop**
  and loss of grasp contact over 1.05 simulated seconds. Policy action count did
  not advance. This was an extra episode, not part of the three-task denominator.

No object qpos/qvel/body poses are edited, no object is welded or frozen, and
resume never resets the scene. Initial-state reset occurs only when explicitly
starting a new benchmark episode. Independent Stop bypasses the LLM and clears
the action queue; stale scene decisions carry a checked physics epoch too.
An already-started simulator interval is identified in traces. The torque
callback can change its control before that interval finishes. Simulated
substep timing is not a hardware stopping-time claim.

One dialogue failure was preserved: Bonsai interpreted “What are you doing?” as
a task start. The execution boundary rejected the scene change. A general
question/negation/hypothetical guard now prevents such starts, even if the model
misclassifies them. Model-selected layouts still require a supported task ID.
Return and arbitrary workshop skills remain unsupported in this lab; the
separate workbench retains its existing tool return/change/resume behavior.

## Run on this prepared workstation

Start the normal workbench first from the fork root:

```powershell
powershell.exe -NoProfile -File .\extensions\workbench\scripts\launch_windows.ps1
```

In a second PowerShell window, from the same fork root:

```powershell
powershell.exe -NoProfile -File .\extensions\workbench\scripts\launch_policy_lab.ps1
```

Wait for GPU warmup and “Ready”, then open `http://127.0.0.1:8896` in Windows
Chrome. Select a bowl layout or click Speak yourself. Try “What are you doing?”,
“Stop”, and “Resume, please.” Motion listening is off until explicitly enabled.
Stop is available during model decisions and inference. A layout change cannot
reset an active/paused episode; finish it first. Native success is labeled as
simulator success, never a hardware claim.

The launcher uses only the three previously prepared locked environments and
verified local checkpoint/observation assets described in windows-migration.md.
It downloads nothing, binds all lab services to loopback and refuses occupied
lab ports. It stops only the processes it started. Ctrl+C closes the lab.
The PowerShell wrapper temporarily unloads the local workbench Gemma vision
alias if it was loaded, then restores it on exit with its verified load settings.
Workbench voice/tools continue, while camera assistance is unavailable during
the GPU experiment. Inspect any restoration warning before camera use.
`-DurationSeconds 5` runs a bounded startup/shutdown check after readiness.

## Validation and remaining work

251 workbench tests pass; 22 separate transport/coordinator tests pass. Protected
upstream byte hashes: 46/46. Changed Python files pass lint/format checks; browser
module syntax and local speech cancellation checks pass. Chrome showed prepared
speech input with recording and motion listening off. Human microphone capture,
echo, audible onset and live interruption latency remain unmeasured.

The actual Windows `-DurationSeconds 5` launcher check passed with exit code 0:
GPU load 18.455 s, discarded warmup 11.053 s, loopback readiness, cleanup of all
owned lab processes and local Gemma restoration. A subsequent real camera answer
used `workbench-vision-gemma`, saw all three tools and left task state unchanged.
Its 2.749 s HTTP wall time is a functionality check, not a latency qualification.

Next: reproduce task-0's contact failure under a new explicit qualification
protocol, broaden policy validation without filtering failures, and complete the
workbench's held-out camera/adaptation work. Its previous reserved result remains
22/24 and rejected against the 95% gate. No learned-policy or camera controller
has been promoted to dependable tool delivery.
