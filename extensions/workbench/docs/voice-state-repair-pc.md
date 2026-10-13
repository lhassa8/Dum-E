# Continuation and planning cancellation repair — PC, 2026-10-13

The human microphone test exposed late Stop and a repeated pickup after
"Proceed." This is a failed live demonstration, not a passing voice qualification.
The matching transcript and decisions are in `runs/dume-2f3fadf5`, the main
8876 session. The camera 8886 run contains earlier automated checks, not this
microphone sequence. No microphone was activated by the agent.

The Stop recording lasts 7.44 seconds; decoding plus recognition is 261 ms.
Native interruption is recorded about 72 ms after `stop_requested`. These
measurements do not locate the user's final spoken word: audio was not saved,
and old logs lack client speech-completion timestamps. Recording duration is
not equivalent to silence or endpoint delay. The acoustic Stop target remains
unverified. New diagnostic headers record capture duration, configured pause,
maximum pending detector frames, and maximum detector inference duration;
server transcript records now include receive/completion timestamps. These
client metrics are diagnostic and never grant motion authority.

The language model classified "Proceed." as `fetch/screwdriver/handoff` in
558.58 ms, and that decision caused another pickup. Continuation now uses
current native/task-manager state before classification, including when a
conversational clarification is pending. Paused work submits resume; active
work gets an acknowledgment; completed work reports its verified result;
idle work asks for the next request. A continuation cannot authorize a fresh
pickup. The native entry point also prevents a supplied resolved fetch intent
from overriding an explicit continuation request.

The baseline ToolDelivery now resumes a release by reopening as needed,
withdrawing from measured joints, and running the original placement judge.
It preserves the original lift history instead of grasping the released tool
again. Three actual physics tests stop at Releasing, Withdrawing gripper, and
Checking placement, then verify success without another approach/grasp/lift.
Four coordinator tests cover completed, paused, working, and idle state, with
pending clarification and no model call.

The camera repair separately resumes cancelled pure camera/IK computation.
An abandoned worker must finish before a new timestamped camera or robot
snapshot is taken. Its result or error is discarded; it cannot become a new
motion plan. Physics and the existing held-tool monitor continue while waiting.
Recovery validates the interrupted phase and finite grasp context before
replacing the closed generator. Grip recovery and release correction retain
their original budgets. Fresh scene observation is attempted first; a bounded
high transit using a previous robot grasp waypoint is permitted only after the
specific missing-neighbor observation refusal, then fresh camera gates run again.

Frozen interruption protocol SHA-256:
`0d9fdcc70e1c34fb4a5368be25fc69c4cb9894d65cba564d4bc2b898d950e558`.
The verifier stops real workers, holds for 32 simulated seconds, and uses
independent simulator truth without changing object state, forces, or judges.
Legacy adapter: 23/23 cases pass (`camera-compute-interrupt-002`). Quiet Mink
run: 21/21 nominal worker phases pass; the two known loss phases are not reached
because that layout completes with zero grip-recovery attempts. They remain
coverage gaps, making the full prescribed protocol 21/23, not a pass.
The earlier Mink run is retained at 20/23, including a stale-frame refusal
while other checks ran. The later quiet success does not prove load caused it.

The running old demonstrations do not hot-reload Python repairs. Alternative
ports can start a separate candidate while preserving them:

```powershell
.\extensions\workbench\scripts\launch_windows.ps1 -CameraTools -AsrDevice cpu -BrowserPort 8986 -SimPort 8985 -McpPort 8804
```

CPU ASR is explicit in this additional instance to avoid allocating another
GPU model. It is not a claim to meet the spoken Stop target. Full speech latency
and a new convincing user-controlled demonstration are still required.

The repaired instance is live at 8986 (`runs/dume-f6e36b53`). An actual typed
bus journey stopped during carrying, resumed on Proceed, verified delivery,
then accepted Proceed as conversation with no new task or job change, and
returned the screwdriver contextually. Observed lift was 212.84 mm; final rack
error was 6.84 mm. Raw trace and rendered final frame remain in
`runs/continuation-live-001`. Existing 8876/8886/8896 services were preserved.
This is one typed sequence, not a microphone latency qualification.

Validation: full Python suite 329 passed in 204.04 s, with 24 existing dependency/
multiprocessing warnings. Speech-library and microphone-capture contract scripts
pass; these use controlled substitutes, not real human microphone access.
Ruff and preserved-byte checks pass; all 46 upstream files remain byte-identical.
