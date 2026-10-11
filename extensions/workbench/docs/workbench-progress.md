# Workbench goal progress

Goal active: docs/workbench-goal.md, adopted October 11, 2026.

Required source: user's accepted goal in this conversation. Priorities are responsive
voice/action, dependable interruption, useful handling and coherent interaction,
expression, perception/recovery, measured learning improvements, hardware preparation.

Constraints: local Mac-first; no hardware/purchases/paid-cloud/expanded microphone
access without explicit approval. Existing fork-branch publication is authorized.
Preserve world-model experiments, original Dum-E interfaces and honest physical checks.
Camera-informed operation and a convincing human live demonstration remain required.

Baseline: fork fd46706, lab a34f8a9; 63 fork tests; interactive tool scene, local ASR,
Stop, return/resume, gestures. Scripted control and privileged simulator observations.
User confirmed live auto-finish/Stop; later voice wording accuracy unmeasured.

Slice A: reproducible responsiveness benchmark and fast bounded command route.
Observed historical model interpretation: 1.609–4.266 seconds across five requests.
Speech pause 900 ms; foreground UI polling 350 ms, bridge polling 120 ms.
Hypothesis: strict routing for familiar explicit commands removes unnecessary model
latency while semantic/ambiguous/unrecognized requests still use the existing model.
Judges: identical 30-case real runtime baseline/post comparison, native task records,
invalid/negated/multiple-tool route probes, full delivery/recovery/Stop regression,
browser operation. Timing endpoints must remain identical and include real ASR.
Rollback: fork fd46706 / lab a34f8a9. Timing targets remain provisional until baseline.

Next slices: responsive interaction during work without losing requests; robust varied
layouts and observed recovery; camera perception with simulator-ground-truth evaluation;
learning experiments justified by measured gains; hardware adapter/plan. Full goal remains
incomplete until criteria and live demonstration pass. Avoid silently shrinking scope.

Available: writable project, Python/uv, local model cache, native simulator, browser
control, tests and Git; IPC/GPU/server/network require reviewed sandbox escalation.
No active permission blocker. Windows workstation availability is unknown.

October 11, first responsiveness pass:
- Same 30 saved-speech trials: common median/p95 2.850/3.122 -> 1.174/1.938 seconds;
  overall 2.889/3.307 -> 1.184/2.838 seconds. Errors 3 -> 0 (negative request fix).
- Strict familiar-command route + complete negative-request decline, model fallback
  for other text. Request/decision/pickup/completion telemetry added.
- Removed serial tool-task nods after observing 1.981–2.118 seconds before approach.
  Greeting/conversation gestures remain. Physics success checks unchanged.
- Found Stop/reset race and transient Stopping phase in probe002; native repeated
  Stop is now idempotent, bridge treats native stop epochs as cancellation. Judge
  waits for actual Stopped; stop timing endpoint remains end-of-utterance -> POST.
- Cold after long idle: 37.05 seconds interpretation, cancelled/discarded. First
  general fallback after restart: 4.84 seconds end-to-decision. These remain visible.
- See responsiveness-audit.md and responsiveness-evidence.json for exact boundaries.
  Saved audio is not live microphone proof. A broader wording/noise/acknowledgment
  benchmark and live demonstration remain outstanding.
- Final validation: 112 lab / 95 fork tests; actual saved-speech Stop 518ms from
  last voiced sample, settled joint drift 0.0000343 rad. Final recovery/return and
  expression integration passes. Pickup starts 1–4ms after native decision in
  observed trials, replacing the ~2-second serial acknowledgment nod.

Next active slice B contract:
- Observed baseline: UI rejects chat during busy work and discards recognized speech
  other than Stop. Original task/native job must remain unchanged by conversation.
- Build responsive task-aware conversation and explicit task changes during work.
  Status answers must reflect observed phase and never imply completed handoff.
  Conversation cannot open a held gripper or replace manipulation waypoints.
- A change to another tool must return a held tool with verified placement before
  fetching the new one, or explain why it cannot. Never release the tool merely
  to accommodate a request. Stop remains independent of model interpretation.
- Judge: actual questions during lift with unchanged task/grip; return redirect;
  varied wording and explicit different-tool changes; original cancelled records
  remain cancelled, new tasks only complete after physics checks; saved speech
  plus browser evidence. Preserve visible controls and motion-only microphone use.
- Rollback for slice B is the committed responsiveness pass. Camera/learning and
  hardware plan remain required subsequent work; goal status stays active.
