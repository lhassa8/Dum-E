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

October 11, slice B verified:
- Read-only task-aware dialogue while manipulating; explicit changes return the
  old tool before retrieving the next; clarification survives task completion.
  Matching negative fetch requests withdraw the request and return the tool.
  Positive Stop invalidates delayed understanding; negative/model-ambiguous Stop
  cannot silently cancel movement. Reset invalidates pending dialogue/context.
- Enabled text/tool inputs during movement and opt-in motion-time speech for
  conversation as well as Stop. Mic scope remains active-work only, visible and
  controllable. Pending recognition survives task completion. Echo comparison is
  a text heuristic, not acoustic cancellation; live room performance remains open.
- Saved short Stop originally failed recognition. Decoder-only 350ms silence for
  sub-second clips fixes that fixture without extra capture delay or confidence
  relaxation. Final shipped voice replay: 519ms end-of-Stop to POST, 0.00173 rad
  settled drift; “don't stop” preserves the running job.
- Empty ready-pose transit fixes poor IK branches after earlier skills; no held
  gripper reopening. Extended runtime found late hammer-return slip (64.6mm).
  Several path/descent/regrasp probes were rejected and rolled back; all retained
  in local runs. Controlled comparison identified weak servo grasp. Doubled
  stiffness produced ~4.6N actuator force and 16.2mm return in the isolated probe,
  versus ~2.3N/62.6mm originally. Gap mapping/force cap/physics checks unchanged;
  real gripper calibration remains required. Three late-return regressions pass.
- Full saved-speech + actual bus/physics journey passes, including model conversation,
  withdrawal, Stop/resume, contextual return and clarification across completion.
  Runtime change placements: screwdriver rack 6.25mm, wrench handoff 7.16mm;
  withdrawn hammer return 13.27mm. A real browser question and change also exercised.
- Identical 30-case warmed replay: 0 errors; common median/p95 1.190/1.215 sec;
  overall 1.204/2.907 sec. Startup-session first recognition took 1.269 sec;
  warmed replay does not prove first-request improvement. First general joke
  during motion took 6.01 sec; clarification/choice ~1.7 sec. Still a bottleneck.
- 135 lab / 118 fork tests, source hashes, Ruff, shipped capture probes and the
  earlier speech/recovery/expression runtime regression pass. See interaction-audit.md
  and interaction-evidence.json. Human live conversation/noise gates remain open.

Next loop A2: isolate general interpretation startup/prompt/decode cost; inspect
local generation tools/cache and compare a bounded optimization. Consider a
smaller local model only after a correctness/latency comparison supports it.
Also make “ready” accurately reflect recognition warmup, measuring startup
separately from first request. Preserve guard, context and Stop behavior, fixed
timing boundaries and physical checks. Rollback is the published slice B commit.
Camera perception, varied-layout recovery, learning gains and hardware plan remain
required; no purchases, real actuation, cloud spend or expanded idle microphone.

A2 loop card (October 11):
- Baseline: fixed 15-case synthetic dialogue fixture, 3 repeats, SHA256
  2f4dd3530e5cc35a59e6716e0dfd96c16d773b989d956d01d87438086875695d.
  Original 45 trials: median 1.500s, p95 1.827s; 6 schema/intent mismatches.
  Three informational tool questions wrongly requested a fetch; three unsupported
  requests retained an object despite the expected nonphysical schema. Neither
  read-only benchmark actuated the arm. Profiling confirms ~0.85s warm prefill.
- Hypothesis: explicit informational-question semantics correct the intent error;
  caching the token-exact fixed instruction prefix removes repeated prefill work.
  Empty physical-action messages remove text that the controller already replaces.
- Boundary: local language prompt, complete per-request cache clone, inference/ASR
  stage telemetry, and reproducible text benchmark. No changed fixture expectations,
  partial-JSON execution, confidence gates, motion checks or microphone scope.
- Judges: identical 45 cases with cache off/on, separate startup cost; context/cache
  isolation checks; existing saved-voice and full physics journey; real browser tool
  question without a fetch. Text timings exclude capture, ASR, audible onset/motion.
- Rollback: lab d4602ae / fork 64ef27f. Attempt budget: two comparable cache probes
  before revising the hypothesis. Broader goal and live room/noise gates remain open.
- Cache probe 001 stopped before readiness: this tokenizer requires a user query
  even when deriving the system template. Add a harmless template-only user marker
  to both prefix probes; it lies after their first mismatch and is never prefetched.
  Retain failed run and fixture unchanged; retry is based on that explicit error.
- Corrected prompt alone: 45/45 correct, median/p95 1.555/1.852s. Cache probe 002:
  45/45 correct, 0.917/1.213s; cached 771 fixed tokens (85.4MB), prefix preparation
  5.292s, total model preparation 11.910s. First request still 3.055s versus 5.364s
  in revised-prompt control. New hypothesis: exercise one read-only decode during
  startup, then mark ready. Measure that cost separately; do not imply it vanished.
- ASR probe after cache runtime restart: first clip 1.924s (decode 0.053s,
  model 1.870s), identical later clips 0.166/0.150s (model 0.139/0.121s).
  Silence warmup skips word decoding. Replace it with a bundled synthetic saved
  phrase through the actual decoder, before ready; expose preparation time. No
  microphone access, task submission or audio output during either warmup.
- Synthetic speech warmup before large language-model startup was insufficient:
  isolated first request still 1.135s versus 0.149/0.143s afterward. Concurrent
  probe was slower and retained separately, not treated as an isolated comparison.
  Changed hypothesis: large-model allocation/prefill after speech warmup leaves
  speech cold again. Order speech preparation after language startup, then measure
  the actual first clip. This is a startup dependency only; active Stop remains
  independent of language inference. No repeated identical warmup attempt.
- Ordered startup first saved clip: 0.214s recognition (0.183s model), then
  0.148/0.149s. First language query after speech still 2.528s: startup preparation
  improves availability but does not guarantee every first model query is fast.
  Isolated final 45-case judge: 45/45 correct, median/p95 0.914/1.224s.
- Same 30 saved-speech replay: 0 errors, common median/p95 1.170/1.217s;
  overall 1.174/2.429s, general 1.735/2.498s. Semantic wording remains >2s.
- New full-journey idle-question check failed: `/interact` submitted all idle text
  as a task before classifying it. Even an answer acquired a native job. Keep the
  failed check; route unrecognized idle text through read-only interpretation
  first, leaving familiar physical commands on their bounded direct route. Reuse
  the classified intent rather than generating it again. Verify no idle question
  job/motion, preserve moving task/grip and previous full speech/physics journey.
- Code review found a larger interruption bottleneck: the capture controller
  awaited a general conversation response before rearming the microphone. Release
  ASR/capture state immediately after dispatch during motion, while surfacing async
  errors. Stop can then be heard while the reply is pending. Also snapshot the
  dialogue epoch at arrival so Stop supersedes requests queued behind a slow reply.
  Judges: shipped-controller pending-promise/Stop probe, queued-request cancellation
  against original shared task store, and real saved speech during pending inference.
- Pending-speech verifier 001 reached Stop and superseded the real pending model
  reply, but its final settling check used a missing frontend joint field. This
  is a verifier API-contract error, not a passing outcome. Read physical joints
  from the native state endpoint (as the earlier settling verifier does); retain
  all criteria and retry with that explicit contract correction.
- Verifier 002 repeated the missing-field problem because the field name was
  assumed. Classify this as a weak tool/API contract: source and earlier verifier
  name the field `robot_joints`. Correct that name and validate its seven-element
  array before moving. Runs 001/002 have no final verification and are not passes.
- Current UI's separate 30-case replay exposed 3/30 failures: present tool need
  after capabilities chat was answered informationally. Original text fixture
  without that history had passed, so it was too narrow to establish contextual
  correctness. Preserve both existing fixtures and failed replay. Add six mixed-
  history cases; clarify current present tool requests versus questions/hypotheticals
  in the prompt. Rerun original 45, new 18 and current UI 30 without weaker judges.
- Final prompt: original 45 and new 18 all pass; UI speech replay 30/30, common
  median/p95 1.167/1.287s, general 1.691/3.111s. Final pending-answer Stop passes
  at 539ms end-of-voice to POST, late answer superseded, drift 2.43e-8 rad.
  Full final physical journey passes: old rack return 6.21mm, requested handoff
  7.16mm, withdrawn hammer return 16.36mm. General joke still 3.29s in that context.
- Browser proved an idle tool question creates no job/motion and a natural-purpose
  request physically delivers a screwdriver. Returned a stopped tool through UI
  at 4.71mm error. A later moving-question observation missed the brief phase;
  it is not counted as a moving-question pass. Use a bounded in-browser visible
  Working wait for the final check, rather than assuming the phase persisted.
  Browser inspection also caught return phases incorrectly naming the handoff
  tray; select the actual rack/delivery label without changing any control target.
- Clean browser proof now passes: one physical job survives the status question
  during visible Working and completes at 9.67mm; browser return at 11.40mm.
  Voice/listening controls restored, public app Ready. Separate headless return
  observes “Moving to tool rack” and measured success. No live room recordings
  published. See dialogue-audit.md/evidence.json and real browser screenshots.
- A2 accepted with remaining limits: individual first/long-idle model delays,
  3.11s UI semantic-request tail, 3.29s full-journey joke, real audible onset and
  room/noise/overlap performance. Neither responsiveness targets nor physics
  thresholds were relaxed. Broad camera/learning/hardware/live-demo criteria remain.

- Final verification exposed a transient mesh read during concurrent export/tests.
  All pinned asset hashes matched afterwards (link3_1: 777 vertices); serial fork
  verification passed 122/122. Direct copy over a live asset is the leading race
  hypothesis. Export now skips identical files and atomically replaces changed
  files; two tests cover whole-file visibility and preservation after failed copy.
  Whole-project export remains a separate operation from verification. Sandboxed
  rerun's 18 IPC errors were environmental (socket binding); IPC-enabled run passed.
- Baseline published microphone controller fails the new pending-reply judge:
  mode stays transcribing instead of listening. Its previous probes pass. This
  synthetic callback control grounds the interruption fix independently of latency.

Next active loop A3:
- Observed bottleneck: current local language model peaks around 20.4GB and takes
  1–3+ seconds for varied/contextual responses despite fixed-prefix reuse. Common
  bounded commands and independent Stop already meet their provisional targets.
- Hypothesis: a smaller maintained local model can improve first/contextual
  latency and memory use while preserving required intent and conversation quality.
- Boundary: research primary model sources, use the existing MLX backend where
  compatible, compare one bounded candidate before changing the default. No paid
  service, new microphone scope, hardware purchase or real actuator. Download only
  ordinary public model data if justified; do not enable arbitrary remote code.
- Judges: original 45 and mixed-history 18 cases, matched startup and UI speech
  observations, factual/capability answers, Stop/context and physical regressions.
  Keep failed cases and original expectations; do not accept speed alone.
- Rollback: accepted A2 source/model; restore current model if the candidate does
  not pass. Then broaden speech/noise evidence and advance camera/learning/hardware
  slices. This is a replaceable implementation choice, not new required scope.

A3 execution — smaller local dialogue model:
- Previous turn classification: progress. A2 code, regression evidence and public
  feature branch were committed; the app is Ready with voice available.
- Primary model card and existing backend code identify a bounded candidate:
  Qwen3.5-4B, converted by mlx-community as Qwen3.5-4B-MLX-4bit. Apache 2.0;
  pinned revision 32f3e8ecf65426fc3306969496342d504bfa13f3; weights 3,034,300,695
  bytes. Download only public data/tokenizer files, never custom Python/remote code.
  Installed MLX-LM has the Qwen3.5 text implementation; vision weights are stripped
  by this text backend. This experiment does not add camera perception.
- Prediction: less memory pressure/prefill cost; quality is unknown. Preserve
  original 45 and mixed-history 18 judges plus the complete speech/physics checks.
  Added 10 fixed reply-quality cases before testing candidate: truthful abilities,
  no camera/feelings/hardware claims, information vs action, remembered dialogue,
  no invented outcome and unsupported repair. Review actual replies as well as
  schema/actions. A fast wrong model will not become the default.
- A first large-model quality run passed 10/10 action/schema cases and manual
  reading found 9 passes and one partial abilities reply (omits conversation and
  an explicit simulation qualifier). First response took 14.53s while the
  candidate download was running; retain it, but do not call that an isolated
  long-idle latency or include it in the matched fresh-start comparison.
- Benchmark now retains HTTP intent/schema errors as failed cases so a smaller
  model's malformed response cannot truncate or disappear from the comparison.

- Candidate download completed after 258.45s; LFS SHA256 matches, no custom code.
  A bounded HTTP range probe worked while Xet kept its output file at zero bytes;
  the confirmed live process then completed normally. No restart/retry was needed.
- Matched fresh large-model control: original 45/45 (median/p95 .900/1.187s),
  context 18/18 (.881/1.247s), quality schema 30/30 (1.071/1.571s). Actual reply
  review: 27 pass, 3 partial abilities answers omit conversation; preserve criterion.
  Current-UI saved speech: 30/30; overall 1.172/2.655s, common 1.172/1.257s,
  general 1.743/2.609s. Model preparation 15.638s, peak allocation 20.441GB.
- First candidate result: original 45/45, .986/1.318s, peak 3.415GB and preparation
  5.502s. It reads the remaining prompt faster, but generates about 45 tokens/s
  and sometimes longer replies. This contradicts the simple smaller-means-faster
  steady-response hypothesis. Do not switch defaults on memory savings alone;
  finish context/reply/speech evidence before deciding.

- Candidate context 18/18 (.807/1.023s); quality schema 30/30 (1.267/1.557s).
  Actual reply review: 24 pass, 6 partial (abilities omissions; webcam answer
  describes sensed tool positions without saying simulator-derived). Original
  expectations retained. These are lead-agent reviews, not a human approval gate.
- Current-UI candidate replay failed 3/30: all "Bring me the wrench and the hammer"
  cases selected fetch/wrench instead of clarification. ASR recognized the exact
  words. This is a decision regression, not transcription. The native fixture used a
  different tool pair; dialogue history also differs. Their respective causal
  effects have not been isolated. Common requests
  18/18 at median/p95 1.162/1.205s; general 6/6 at 1.552/2.091s. The lower latency
  does not justify unintended tool selection. Restore accepted model; do not
  change defaults, add a fallback parser or weaken the multiple-tool judge.
- A3 candidate rejected for default use. Fixed native tests were too narrow to
  represent the complete dialogue route. Preserve its actual failure and same
  public-speech judge. Next hypothesis: explicit ambiguity/capability handling
  and concise replies may help, but test every pair of supported tools in realistic
  prior conversation before any new model/default decision. No additional model
  download is needed to investigate this observed failure.

- Restored browser independently answers the wrench/hammer ambiguity after
  capabilities chat with "Which tool would you like first?" Native job null,
  zero physical tasks, maximum tool drift 1.65e-8m. Tray reset clears pending
  clarification. App Ready with voice and active-work listening restored.
  Session: extensions/workbench/runs/model-restored-runtime-001. Evidence and
  real screenshots: model-comparison-audit.md/evidence.json and model-restored-browser.png.
- A3 bounded comparison complete; candidate rejected, full goal still active.
  No runtime/prompt/default/dependency/vendor change. Added a reusable quality
  fixture and benchmark error retention; saved measured successes and failures.

Next active loop A4:
- Isolate the multi-tool ambiguity across all supported pairs and prior dialogue.
  Native fixture used screwdriver+hammer; speech used wrench+hammer with retained
  chat, so do not assume a single cause. Preserve all original cases/expectations.
- Investigate concise, explicit capability/perception instructions using the
  current downloaded models; no additional download yet. Prediction: fewer
  unnecessary tokens and clearer factual replies without losing correct intent.
- Judge: original 45, mixed-history 18, quality 30 actual replies, same current-UI
  30 saved speech, then independent Stop and real physical regressions before
  accepting any model/prompt change. Accepted A2 default is the rollback.
- Limit model tuning to two evidence-driven attempts; if still unreliable, keep
  accepted model and advance noise/perception/learning/hardware slices instead
  of turning the product goal into an indefinite language-model benchmark.
