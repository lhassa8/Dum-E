# Workbench goal progress

October14 — training-only calibrated grasp teacher:
- Prospective state split excludes prior evaluation0; training1–4,
  validation5–6, final7–8. Access only task0 training1/2. No weights trained.
- Correct native box-vs-mesh calibration; preserve invalidsurvey001. Teacher001
  gets bilateral pad contact but both220-step budgets expire in lift. Diagnose
  conservative travel; shorten approach and increase bounded native commands.
- Teacher002 passes2/2 but lacks saved initial height. Repeat003 with initial
  truth and actual hold frames:2/2,102/91active steps, minlift115.799/110.925mm,
  translation1.311/5.227mm, jointrange0.520/0.578mrad,547dense samples each.
  Independent raw-record/source/input audit passes; local front/wrist videos.
- Same two training states repeated, not broader generalization. Privileged
  teacher only; no learned-policy or placement/release claim. Full-task prompt
  currently exceeds demonstrated prefix. Next extend through verified release
  and resting placement before complete action-chunk adaptation. Public actor
  unchanged;46upstream bytes preserved. See [teacher audit](grasp-teacher-audit.md).

October 14 — post-restart whole-assistant requalification:
- Baseline25201a1, no WSL assistant/native/MCP services alive. Restore camera
  voice profile at8996 with local Bonsai/Gemma, CUDA general ASR, CPU Stop, SAPI.
  Select local Gemma explicitly from duplicate-key menu; deviceIdentifier=null.
- Current typed full Stop/resume/tool-change/return sequence passes. Retained
  natural saved speech also delivers/returns from continued scene without reset:
  recognition174.86ms, native decision517.82ms, lift214.3mm, handofferror22.8mm.
- With1.5GB freeGPU, close only ownedidle8996 while isolated9036 runs original
  six frozen full saved-stream journeys. Actual browser VAD/ASR/models/taskbus/
  native camera physics/Windows output: independent6/6, all12 placements pass,
  minlift201.35mm,maxerror8.47mm,sampled settleddrift0.000057rad/heldmotion0.071mm.
- Conservative browser-clock nativeStop upper bounds761.85/846.90ms med/p95,max
  n6. Five native-verified pendingcamera replies superseded. No relaxed judges.
  All24 requiredacks/42 replies finish;ack51.35/91.90ms n24,APIplayer76.20/129ms
  n67. One additional begun utterance cancelled intentionally; no acoustic proof.
- Evidence checker has six TOTAL records: positive control plus five negatives;
  correct old "six altered" label/prose, keep logic/rawdata unchanged.38 targeted
  Python regressions and recorder/output/observer contracts pass;46 upstream hashes.
- Close ownedtestservices, restore8996 cb993cb1 Ready. Both models now manual
  no-TTL residency, context4096/one slot. Two fresh camera probes1.474/1.024s see
  allthree tools without motion; n2 is not broad/longidle/heldout qualification.
- Human-owned microphone check requested again after actual restoration; no
  microphone activated by agent. Rawdata/renderframes local. See
  [restart report](pc-restart-requalification.md). Goal remains active: human room
  timing/echo, broader camera recovery and pretrained-policy Stop/holding open.

October 14 — local LFM2.5 comparison:
- Verified the official QAD Q4_0 GGUF and its independent LM Studio import copy
  against pinned publisher bytes/SHA-256. Actual inference used the CUDA12 2.57.0
  engine, context4096/one slot; no microphone, motion or hardware calls.
- Four read-only runs each attempted all31 fixed requests three times. Bonsai
  existing/native profiles score93/93 and78/93; LFM scores38/93 and81/93.
  The LFM larger budget has six unwanted fetches on unsupported tasks, three
  missed contextual wrench requests and three capability truncations. Rejected
  as current interpreter replacement; no prompt retuning or failure relabeling.
- Correct-only median485ms Bonsai existing versus1,322ms LFM native. Sequential
  runs with other desktop GPU applications active; no isolated latency or camera
  contention claim. Full raw source/fixture/row audit passes allfour runs.
- Candidate unloaded by its own identifier; checkpoint/cache/reports kept local,
  Bonsai remains resident. WSL restarted since prior turns: previous simulator
  demo processes were absent, so no present Ready/demo/microphone claim.
- New evaluation/preparation/audit helpers lint clean;46 upstream files remain
  byte-identical. See [the evaluation](lfm-local-evaluation.md) and evidence JSON.

October12,B13 — pretrained vision and read-only camera questions:
- Previous goal turn was progress: stable placements published at lab13d6d2e /
  fork8fb6ec4. Revalidated unchanged running main Ready/Bonsai/contactsv2.
- Reused cached pretrained models via existing LMStudio/LMLink,no downloads or
  real camera/mic/paid access. CLI now verifies Bonsai on linked workstation.
  Mac-native UI locked; supported CLI/API remained usable. Duplicate CLI model
  keys can pick local copies; rejected before prediction and cleaned up. Explicit
  selector binds the chosen workstation copy; no new credentials/link scope.
- Bonsai misses tool identities; kept for conversation. Gemma12B Mac pilots
  correct but6–9s. Qwen27B default5.69–8.38s; explicit GPU configuration1.05–1.63s
  on same pilot images. Expanded/compact Qwen validation9/10,8/10 with absent
  false positives; rejected. Gemma31B compact first rejects coordinate contract;
  retained output reveals1000-grid[y,x]. Explicit convention/strict normalization
  passes same unchanged40px judge; no clipping or auto-unit guessing.
- Ten frozen validation scenes now10/10,no absent false positives,max10.53px
  center error;median1.083s,p951.273,max1.398. RGB/catalog only,no pose/inventory
  data sent. This is conversational image grounding,not5mm motion qualification.
- Camera questions are pure answers,never robot commands. Capture on main thread,
  fresh JPEG cache,independent vision lock,Stop invalidation,snapshot hash checks.
  Camera/model/unit/endpoint choices explicit;different-camera native reuse fails.
- First real saved-speech/task-bus/physics journey passes all stages except final
  post-return camera identity: shadowed screwdriver missed. Retained snapshot and
  failure. Added bounded second optical view without light/geometry/pose changes,
  never filling from state or mixing coordinate frames. Same unchanged journey
  now passes;32.04-wall-second hold min224.22mm,joint drift0.00395rad;Stop63.96ms.
- Alternate-view validation preserves10/10/zeroabsentFP but one2.126s recovery
  misses2s target. Real post-return recovery2.225s;tail gap explicitly retained.
  No new live-speech/settling claim. Camera-based robot motion remains separate.
- Final lab263/fork244 regressions pass;all46protected upstream hashes unchanged.
  Main8766/native8765/MCP8001 restarted at exec74724 with Bonsai+Gemma camera.
  Actual browser camera button verified RGB-only answer,no physical job. Main
  saved-speech/Stop32s/resume/return journey independently passes;all tools rack.
  Final screenshot/voice restoration retained after checks;candidate cleaned up.
- Full goal active:camera-derived motion,pretrained arm runtime,real acoustics
  and convincing human live demonstration remain. No reserved C3 test opened.
- See vision-language-audit.md,synthetic evidence,comparison and recovery traces.

October 12, B12 — stable returned tools without weakening Stop holds:
- Previous goal turn was progress: Bonsai/configurable backends published at
  lab4892e9e / fork52c4b4f. Kept the user's selected model and Mac speech setup.
- Reproduced old contact creep: all9 frozen tool/seed trajectories fail4mm
  displacement over1800 simulated seconds after physical return (31.12–71.68mm).
  NoSlip tolerance tightening did not change drift. Global elliptic contacts
  failed retained seed51/hammer Stop height; rejected without weakening the gate.
- Fixed explicit sliding-only tool/table contacts while keeping gripper contacts6,
  NoSlip3, geometry/masses, original force caps, controller and finger coupling.
  Actual contact inspection verifies dimensions/friction/solver parameters.
  No object weld, pose/velocity freeze, engine sleep or phase-based physics switch.
- All9 candidate trajectories pass unchanged32s Stop holds, delivery/return,
 1800s idle and real re-pickup. Peak drift below0.001mm;27 placements6.98–14.46mm.
  This is deterministic simulation evidence, not a real-world precision claim.
  Fixed protocol/hash and independent numeric review retained. Recorder failure
  rejected; explicit scalar conversion, atomic checkpoints and short real pilot
  precede complete rerun. Production stepping unchanged (no speed benefit found).
- Full lab238/fork219 tests pass, including original nine drop/hold and six
  continuation regressions. Added actual contact/release/idle/re-pickup contracts.
  After a small launcher SIGTERM cleanup correction,43 focused tests pass each.
  Real isolated shutdown releases UI/native/MCP ports in0.821s with exit0.
- Launcher rejects stale/unknown contact profiles. Owned main restarted with
  Bonsai/tool_contacts_v2, exec87296; old Ready snapshot saved before replacement.
  All three32-wall-second Stop holds + physical continuation/return pass.
  Pending model reply superseded1.142s, next model request works; typed Stop
  observed6.35–59.86ms. No new voice-boundary/settling/tail-latency claim.
- Saved synthetic speech passes request change/Stop/resume/contextual return,
  withdrawal,general Bonsai dialogue and clarification across completion. Browser
  independently Ready,tools on rack,Voice/listen ON,mic idle; screenshot retained.
- Historical camera/carry/release learned weights need requalification under
  changed contacts. No reserved camera test opened. Full goal active: public
  camera-informed operation, actual pretrained arm runtime, acoustic/live human
  demonstration remain; no bespoke controller sweep substitutes for model reuse.
- See idle-contact-audit.md, synthetic evidence bundle and measured comparison.

October 12, B11 — user-selected Bonsai and replaceable conversation models:
- Previous goal turn was progress: published B10 grip/latency fixes at lab
  ae62140 / fork6213fe2. User loaded Bonsai on the preferred 5090 device and
  requested trying it, with future model flexibility.
- Actual LM Studio ID prism-ml/bonsai-27b, Q1_0, reported4.735GB/27B parameters,
  loaded8192context. API does not identify the executing device; retain the user's
  host/preference report without inventing GPU telemetry. No model download/load,
  device-selection change, paid service or expanded microphone/data scope.
- Initial129intent checks pass but abilities omits simulation3/3. One shared
  scope instruction fixes that factual failure; unchanged43cases×3 now pass129/129
  and lead-review30factual replies meets original criteria. Some repetitive
  capabilities remain a style limit; original replies are retained.
- Final129 text trials median/p95 .560/.760s, max1.149s. Alternating5cases×2
  matched pair: Bonsai .510s vs Luna2.407s median (78.8% lower), zero errors;
  retain Luna12.360s outlier. Excludes voice/motion and other-device contention.
  Selected model ID is returned correctly, not an independent weight hash.
- CLI provider/model/server choices are shared by launcher/native; LM Studio
  no longer guesses Qwen. Explicit MLX folder, LM model/endpoint and fixed Luna
  choices cannot silently reuse another setup. Substitution/timeouts fail without
  motion/retry; next request recovers. No model-specific control/parser branch.
  Full234lab/215fork suites pass, plus a local-folder reuse guard afterward;
  final34focused transport/API checks pass each. Upstream46hashes match.
- Main8766/native8765/MCP8001 now use Bonsai. Actual three32-wall-second holds,
  resume/return and pending-reply supersession pass; errors6.09–13.90mm. Reply
  supersession observed within308ms; remote inference may continue.
- Synthesized semantic speech is recognized, model-interpreted and physically
  delivered/returned (9.48/11.72mm). ASR upload .152s, native decision .736s:
  separate clocks, not end-of-live-speech latency. Existing complete saved-speech
  change/Stop/resume/return/withdrawal/clarification sequence passes; real Bonsai
  joke during lift .850s keeps task running. Browser abilities answer is truthful;
  voice/listening restored ON with microphone idle.
- Secondary camera recheck before model steering passes18/18 for an optional
  linear-lift/centering variant, not a contact-only baseline. No promotion or
  reserved-test opening. Reusing robot policies remains the manipulation direction.
- Old main preflight finds screwdriver72.67mm from its earlier successful rack
  placement while idle. Snapshot retained; cause/exact time unproven. Conversation
  model selection does not fix this long-idle physics gap. Next investigate it
  while preserving held-tool checks. Full goal active: public camera operation,
  pretrained arm runtime and human live/noise proof remain open.
- See bonsai-audit.md, evidence JSON, comparison and ready screenshot.

October 12, B10 — paused grip and subscription latency:
- Reproduced the long-hold failure across all nine tool/seed combinations. Soft
  friction contacts creep and an uncompensated arm position hold sags. Three
  NoSlip contact iterations plus gravity feedforward in paused arm targets now
  pass 9/9 unchanged 32-s retention gates. No object weld/pose freeze, grip/force
  cap change or relaxed physical judge. Nine opening-finger drop tests and six
  long-hold continuation tests pass. Historical learning results use old contacts;
  NoSlip's inverse-dynamics/contact limitations are documented.
- Persistent official Codex app-server; fresh ephemeral context per utterance,
  process-scoped host-tool/skill isolation, ChatGPT account required, no API-key
  fallback. Stop interrupts the active turn; queued stale requests are skipped.
  Runtime cleanup closes the subscription child with the native simulator.
- Alternating same-model/same-schema paired test: 10 calls per path, zero errors;
  median 3.332 -> 2.642 s (20.7% improvement), input tokens 7,329 -> 5,780.
  Sample p95 worsens 4.089 -> 6.664 s due to a retained cloud delay. Do not claim
  reliably improved tail or voice latency. Separate 43-case qualification passes
  once each, factual replies reviewed against the unchanged content criteria.
- Actual task-bus/main-app Stop + 32-wall-second holds + resume/return pass for
  all three tools; placement errors 6.09–13.91 mm within the unchanged 35 mm gate.
  A real pending Luna reply is superseded by Stop with no task and observed within
  70.7 ms; next model question works while grip stays closed. This is typed HTTP
  cancellation, not live spoken Stop or mechanical velocity-settling evidence.
- Full regressions 224 lab / 205 fork, plus two new authentication/protocol cases
  checked afterward in each checkout; focused transport/API suite nine passes
  each. Protected upstream 46 hashes intact. Final main app remains 8766, now
  native 8765, subscription Luna; no new purchase or microphone scope.
- See hold-luna-audit.md / evidence JSON / comparison for scopes and retained
  failures. Full goal remains incomplete; next large improvements concern live
  voice/room responsiveness and camera-informed default tool handling. Actual
  pretrained arm policy still needs a supported OpenPi workstation runtime.

October 12, B9 — user-requested conversation hosting options:
- User connected Qwen3.8-27B through LM Studio/LM Link and confirmed the RTX 5090
  PC is preferred. Implemented opt-in HTTP inference; structured output resolves
  three original JSON context failures. All 129 action/object checks pass, but
  reply-quality simulation disclosure and latency prevent default promotion.
- User then explicitly authorized ChatGPT subscription hosting with GPT-6 Luna.
  Implemented official ChatGPT-signed-in Codex CLI inference, ephemeral read-only
  requests, bounded schema, disabled agent capabilities and no API-key fallback.
  General request text/context/simulator observations go to OpenAI; capture,
  transcription and simulation stay local. No new purchase or microphone scope.
- 43 distinct frozen cases pass once each; do not compare this sample's tail
  directly with the prior three-repeat studies. A retained 30-second cloud timeout
  prompted explicit failure/next-request recovery. 203 lab / 184 fork regressions
  pass, protected upstream hashes intact. Main app 8766 now uses Luna/native8785.
- Actual typed model request delivers screwdriver with 9.666 mm error and 204.935
  mm lift. Pending real cloud reply is superseded by Stop, but the physical
  stop-time retained-tool gate fails: screwdriver slips to table height. Existing
  contextual return recovers with 5.211 mm rack error. No physics gate or controller
  was changed to manufacture a pass. Evidence in codex-luna-audit.md and JSON.
- Conversation-hosting request is implemented; full project goal remains incomplete.
  CLI overhead/cloud jitter, stop-time slip and live voice remain open. LM Studio
  and Luna inference do not expose a Windows shell or run the pretrained arm policy;
  actual OpenPi/LIBERO manipulation still needs a supported workstation runtime.

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

A4 execution — clarify ambiguity and shorten truthful replies:
- Previous goal turn classification: progress. A3 measurements, retained failures
  and public commit changed the model-selection decision; accepted model restored.
- [O] Current prompt already says multiple tools require clarification, but names
  "current sensor data" elsewhere despite simulator-only inputs. That conflicting
  wording can invite vague sensing claims; exact causal effect is unproven.
- [S] Preserve one-tool ambiguity, factual capability/scene explanations, existing
  speech interruption and physical outcome checks. [D] A concise reply instruction
  is a replaceable implementation choice, not a new user-facing feature.
- Frozen 12 new pair/context cases before mutation: three supported pairs under
  fresh, capabilities and fetch/decline history, plus single preference, information
  and negated pair controls. First collect large/small unchanged-prompt probes;
  then one bounded wording change. At most two evidence-driven revisions.
- Hypothesis: explicit current-utterance selection and complete clarification JSON,
  consistent simulator terminology and a short spoken reply budget improve decision
  clarity and response time. Judge native fixed fixtures/actual replies, then same
  30 speech cases and independent Stop/physics before accepting a change. Rollback
  is accepted A2 prompt/model; no parser fallback, threshold or fixture relaxation.

- Unchanged accepted model: 12/12 pair/control decisions correct. First response
  after the existing app's idle interval took 17.263s despite model_ready; later
  responses .761–1.303s. This is a loaded-model long-idle observation, not a fresh
  startup claim. Paging/kernel residency is a hypothesis, not proven causation.
- Unchanged small model fails 6/12, including fresh screwdriver+wrench and multiple
  prior-chat combinations; fresh wrench+hammer alone passes. Both pair and history
  affect outcomes. Cache-disabled control fails 7/12 with the same contract; cache
  reuse is not a sufficient explanation. This strengthens a model/decision-contract
  diagnosis rather than a recognizer or simply stale-cache diagnosis.
- Attempt 1 changes only instruction wording and familiar capabilities reply:
  complete multi-tool clarification JSON, current-utterance selection, preference
  vs requested pair, coherent simulator-only terminology, explicit chat capability
  and an aim of one short sentence/25 words. No output truncation, parser fallback
  or weakened intent expectation. The new paired example is screwdriver+wrench;
  other pairs/histories still judge generalization.

- Attempt 1: pair fixture 36/36, context 18/18, quality intent/schema 30/30;
  original fixture fails 3/45: casual chat incorrectly selects a wave. Actual
  quality reading finds three capabilities omissions (conversation), and three
  success-denial replies wrongly allow a request alone to establish delivery.
  Kept all failures. Attempt 2 explicitly limits gestures to greetings/requests,
  gives a complete short abilities reply, and says only verified controller
  results establish success. Same fixtures, complete JSON and motion judges.

- Attempt 2 native decisions: pairs 36/36, original 45/45, context 18/18,
  quality schema 30/30. Actual reply review still finds three abilities replies
  omit simulation and three denials describe an incorrect request-or-movement
  success condition (no actual false delivery was asserted). These remain
  partials, not clean factual passes. No third prompt revision; finish the
  matched speech observation and retain a conservative default decision.

- A4 final: both models pass original45/context18/pairs36/quality-schema30
  and current UI speech30. Large actual quality30/30 complete; small24/30
  complete,6 factual partials. Keep large default and adopt the tested concise
  prompt. Small remains experimental; no third wording revision or new model.
- Kept model speech common median/p95 1.174/1.247s; general 1.688/2.341s,
  guards1.711/2.350s. General tails improve modestly vs preceding matched study;
  only six trials per category. No audible-onset/live-room claim. Large startup
  sample20.451s; prefix11.604s. Long-idle17.263s still unsolved.
- Independent original pending-reply Stop passes:593ms end-of-voice to POST,
  late reply superseded, task cancelled, grip retained, drift3.56e-7rad. Full
  speech/physics journey passes: rack6.20mm, handoff7.16mm, withdrawn hammer
  rack16.30mm. Moving joke3.186s (first token2.593s), still a bottleneck.
- Fresh full regressions141lab/122fork, Ruff/format pass. Original46file hashes
  intact. Evidence: dialogue-revision-audit.md/evidence.json, figure and browser
  proof. Public app restored on accepted large model; goal remains active.

Next active slice D1 — grounded simulated camera observations:
- Previous goal turn classification: progress. Bounded language study completed,
  errors retained, prompt accepted, unsafe default switch rejected. Advance a
  different required capability rather than repeat model tuning indefinitely.
- [O] Tool localization currently calls privileged simulator positions; RGB
  overview rendering already works but no camera-derived tool estimates exist.
  [S] Adopted milestone D requires camera-informed operation and varied layouts.
- Hypothesis: calibrated rendered RGB (and depth if justified) can identify and
  localize the supported tools well enough to support later retrieval. Start with
  an offline perception baseline and measure before trusting it for movement.
- Boundary: modular frame/calibration inputs, a small reproducible varied-layout
  dataset, detector/localizer and error/occlusion visualization. No webcam/mic
  permission, real arm, giant model download or changes to accepted manipulation.
  Select classical geometry/color or a small learned baseline from measured
  evidence; report markers/known-geometry assumptions if used.
- Judge: separate fixed held-out scenes, actual rendered RGB/depth inputs only;
  simulator positions/IDs allowed in dataset labels and evaluation, never in
  detection or a silent miss fallback. Report misses, wrong identities, mm
  localization error and confidence under occlusion/varied layouts. Freeze
  examples and provisional criteria before tuning; integrate motion only after
  independent accuracy and physical checks. Keep existing Stop/task regressions.
- Rollback: accepted A4 runtime. Camera baseline does not itself complete D.
  Learned-model usefulness, failure recovery, acoustic/noise testing, hardware
  adapter/plan and the convincing human live demonstration remain required.

D1 execution — actual simulated camera baseline:
- Previous goal turn classification: progress. A4 prompt, full regression and
  browser/physics evidence published at fork cd0ed4b; root4379b90.
- [O] Installed MuJoCo3.15.0 classic Renderer provides RGB and metric axial
  depth; existing overview is distant. [D] Probe a fixed overhead camera at
 640x480 with zero stereo offset, using known calibration. This changes only
  offline scenes, not the accepted public simulator or upstream assets.
- First inspect an actual frame before selecting a detector. No new dependency
  or marker assumption yet. Freeze varied-layout held-out examples before tuning.

- Overhead probe is substantially arm-occluded; retained RGB/depth. A bounded
  three-view sweep identifies a front oblique camera with all tools visible.
  Selected1.05,0,.9m,40deg,640x480,zero stereo offset. Classic OpenGL warns
  about clip-control precision; independent rendered mat-plane check passes
  below0.5mm, so depth is measured rather than assumed unusable or perfect.
- Frozen48scenes before tuning:12pilot,24held-out clear,12held-out occlusion;
  yaw rotations, shuffled rack slots, x/y offsets and lighting variation. SHA
  3c88327d24eefceaaec2769a80e4fc3860110c35e98c63c31c2bc2bfc02e46b4.
  Provisional gate:95%clear coverage,p95position5mm,no confident occluded or
  identity-confused estimates. RGB/depth/calibration files hashed separately
  from privileged annotation labels; detector has no simulator imports.
- Classical baseline uses colors, depth and known44x56mm flat handle tops; no
  markers, pretrained vision model, privileged rack coordinates or miss fallback.
  Pilot36/36 observed,median0.49mm/p950.67mm; one wrench outlier5.29mm retained.
  Held-out72/72 clear,p950.67mm,max0.73mm; all12occluded targets withheld. One
  additional unoccluded wrench in an occlusion scene is conservatively withheld
  as ambiguous. Median localizer23ms,p9526ms excludes rendering/IO/planning.
- Independent tests:actual rendered unseen rotated/permuted layout,known mat
  depth scale,occlusion,no-depth refusal and duplicate-handle ambiguity pass.
  First analytic projection probe used zero absolute tolerance at expected0;
  its2.22e-16roundoff is not a camera failure. Corrected arithmetic-only bound
  to1e-12m; fixed5mm benchmark and0.5mm actual plane checks unchanged.

- D1 offline baseline accepted:held-out72/72 clear tools,p950.67mm, all12
  occluded targets withheld; independent duplicate-handle/no-depth probes pass.
  Actual capture+localizer32ms median/36ms p95 across30 stationary captures,
  scene prep288ms, firstsample52ms. This excludes active manipulation/IPC/IO.
  Fresh147lab/128fork, Ruff/format pass, pinned46upstream hashes intact.
  No dependency/model/voice/controller changes. Camera-perception audit, public
  synthetic evidence and actual rendered comparisons saved; native warning
  logs remain local. The public app continues on the accepted A4 runtime.

Next active slice D2 — camera estimates guide actual pickup:
- [O] Current PickPlace/ToolDelivery use bench.observe for approach, grasp-lift
  checks, carried-tool offsets, recovery and final outcome; support_height also
  uses privileged tool geometry/pose. Initial camera target substitution alone
  would therefore be a hybrid, not proof of a camera-based controller.
- [S] Adopted milestone D requires camera-informed operation on varied supported
  layouts. [D] Build a separate experimental observation/planning adapter before
  changing the default public controller. Preserve the accepted A4 rollback.
- Hypothesis: fresh camera estimates plus robot joint/gripper proprioception can
  support contact-based pickup/delivery while independent simulator truth judges
  outcomes. Reject ambiguous, stale, low-fit or missing camera targets before
  moving; never silently substitute rack coordinates or true tool positions.
- Start by separating motion inputs from verification. Inspect actual pose/offset
  assumptions, camera occlusion near the gripper and supported orientation.
  Bounded first physical probes, then varied layouts and regression journeys;
  retain failures and do not relax original placement/grip/Stop checks.
- Camera observation must have visible provenance when exposed in the app;
  update the assistant truthful capabilities only after integration works.
  No webcam/idle microphone/real actuator or new model required for this slice.
  D1 does not complete camera operation, recovery, learning, acoustic/noise,
  hardware adapter/plan or the required human live demonstration. Goal active.

D2 execution — camera-informed physical actor, October11:
- Previous goal turn: progress. D1 tested optical baseline published at fork
  d6c5b1f5c67addd9c045f1ec99497af841617733/root4f14055; exact remote verified.
- [O] Actor receives timestamped RGBD + narrow robot joints/TCP/gap/clock port.
  It has no bench/model/true tool positions; actual tests deny observe and
  support-height access while all3tools physically lift/place. Outcome judge
  remains separate and actor reports released_unverified, never success.
- [D] Provisional motion gates: fit>=.8, age<=.25 simulation seconds, finite
  tabletop pose/yaw; no missing/ambiguous/cached/NaN fallback. Known handle
  dimensions/colors, tabletop faces and catalog clearance remain assumptions.
  No hardware/webcam/model/dependency or public voice/controller change.
- Frozen15cases (3pilot,12varied) before first actor; SHA
  acb1b93171a78e0b1589f98a88187a077562749896a6985f7cd50ee359335e72.
  Original lift80mm,placement35mm,height40mm,speed30mm/s,disturbance4mm
  preserved; hold608ms/gripretained/jointdrift<.03rad and95%journey gate.
- First pilot0/3refused; rectangle-only revision0/3refused. Actual RGB/depth
  diagnostic shows highlights lose material hue; PCA/partial edge geometry
  biases shape. Changed hypothesis to color identity seeds plus connected
  measured depth plane and minimum-area rectangle. Pilot2/3physical passes;
  straight hammer fit.768stillrefused. No motion-gate lowering.
- New fitter passes untouched D1judge72/72clear,p95.257mm,max.404mm,12/12
  obscured withheld/noidentityconfusion; old5.29mmoutlier now.10mm, pilot
  maximum.529mm. Historical evidence retained/versioned.
- Final frozen12initial moves physicallypass; 8fresh-camera handoff-to-rack
  returns physicallypass; 4resume+4heldredirect pass their placement checks.
  Full journey11/12fails95%gate: hammer returnheldout05nudges screwdriver
  4.14mm beyond4mm. All8holds retaingrip,maxjointdrift.00572rad.
- Stronger verifier exposed omitted secondary-return disturbance and redundant
  already-rack regrasp counting. Corrected combined verdict, retained prior
  incomplete summary and all failures. No thresholds weakened.
- Evaluator-only diagnostic: actual held hammer differs from rigid-grasp
  estimate by~10.4mm before descent; neighbor moves during descent/release.
  [I] Carried-pose uncertainty is the next limitation (high confidence); exact
  slip/servo/contact decomposition unknown. Constant rigid grip is invalidated
  as a sufficient assumption for full camera journeys.
- Serialized capture+pose59.7msmedian/64.8msp95,prep297ms/first95ms. Earlier
  probes overlapped physics/regressions and are separately labeled; they are
  not clean speed comparisons. Extra fitting increases cost from D1~32ms.
- 17focused optical/denied-truth/grip/staleness tests pass. Full lab regression
  verified158pass; independent exported fork139pass; Ruff/format pass and
  all46upstream hashes match. Scientific actual-frame
  figure inspected. Controller remains experimental; public A4rollback stays.

Next active D2b — carried-tool drift and full-loop acceptance:
- Address the measured failure through actual held-tool perception or a learned,
  validated dynamics estimate from camera pose + robot telemetry. Declared
  catalog assumptions and inferred poses need explicit uncertainty/provenance.
  Do not fix the failed case by weakening4mm or adding true-pose offsets.
- Use independent training/pilot trajectories for any slip model and freeze new
  untouched layouts before tuning. Preserve all15existing camera cases and the
  failed full-journey judge; compare physical outcomes, not just model RMSE.
- Resolve straight-hammer viewpoint/refusal and all-phase recovery before
  replacing the public controller. Then integrate observation provenance and
  exercise complete saved-speech/chat/Stop/change/return journeys with images.
- D2 prototype does not complete camera operation. Useful learned-model gains,
  acoustic/noise testing, hardware adapter/plan and required convincing human
  live demonstration remain open; full goal active.


D2b execution — learned carried-position estimation, October 11:
- Previous goal turn: progress. D2 published fork c753d00/root be1cd06; exact
  remote verified. Full goal remains active; public A4 controller stays Ready.
- Frozen 54train/12validation/24test layouts, SHA
  265ae7aedb6c05fc7fe99b96eafbdb4f32b38629a0d92b7b774531aed7887e86.
  Physical judges unchanged, including4mm disturbance/35mm placement/95%journeys.
- [O] First39-feature MLP validationp95 7.06mmfails5mm gate. Training journeys
  were correlated with identity. [D] Added a frozen72-training-only balanced
  extension and robot joint-velocity/actuator telemetry before second fit;
  validation/test/criteria/hyperparameters unchanged. No third blind fit.
- Camera full-direction cue uses observed distal metal/depth; unknowns remain
  unknown. 35/36pilotdirections, max1.82deg againstinitialyaw; independent
  rendered true-body heading tests pass. D1clear72/72,p95.257mm and all12
  occlusions withheld. Signed direction is not a general vision model.
- Candidate2 is54features/7875parameters;6096rows/118train episodes,604rows/
  12heldvalidation. Eight training trajectories zero-row, outcomes retained.
  Camera history+robot telemetry only; truth labels exclusively outside actor.
  Target is current free-space carried-position residual, not next-state model.
- Matched603validation samples: rigidRMSE12.976mm vslearned2.159mm,
  learnedp954.372mm/max7.309mm. Oneout-of-range row withheld; offlinegatefails.
  Bounds are provisional, not calibrated uncertainty. Original evaluation
  raised after checkpointwrite; re-evaluated unchanged checkpoint, no refit.
  Candidate2 trainingduration unknown; never fabricated. Runtime NumPy only.
- First policy(fullXYZ) fixedoriginalhammer4.14→1.51mm but fulllegacyjourneys
  worsen11/12→10/12 due2fresh-return refusals. Second policy retains transport,
  onlyXYdescent correction: again10/12. Both rejected for default.
- Untouched24tests opened only after policies fixed: rigid21/24 vslearnedXY20/24;
  bothfail95%gate. Shared2weak-fit refusals and1unreachablepose; learnedadds
  direction-refusedreturn. No tuning after tests. Existingcases nowregressions.
- [O] Truth-only screwdriver diagnostic shows actual-minus-rigidX changing
  +13.45mm beforedescent to−3.36mm beforerelease. NNdescent correction+9.63mm
  corresponds tofree-space estimate, yet contact changes needed correction;
  placement8.71→18.60mm. [I] Missingfuturecontact/releaseprediction capability,
  highconfidence; precise slip/servo/force decomposition remains unknown.
- Serialized opticalpipeline73.4/76.1ms median/p95,prep293ms/first97ms;
  priorD259.7/64.8ms is a separate stationary run. Addedheading costs time.
  NNstandalone3.507/3.797ms initially; samecheckpointfinal3.526/3.936ms.
  Small relative to optical and existing voice/LM delays; no live latency claim.
- Root20focused/full161tests and Ruff/format80files pass. Experimental rejected
  checkpoint, collector/trainer/verifier, fixedfixtures, evidence and scientific
  figure exported to fork. Independent142forktests and Ruff/format56files pass;
  all46pinnedupstreamhashes match. Scientific figure inspected.
  No dependency changes, new microphone/webcam access, hardware or purchases.

Next active D2c — predict contact/release outcomes and recover observation:
- Replan after two failed policies; do not tune more offsets or weaken judges.
  Learn future placement consequences from camera/proprioception plus proposed
  action, include table contact/release, compare physical utility against rigid
  and simple baselines. Freeze new independent train/validation/test scenes;
  keep all opened D2/D2b cases as regressions, not fresh generalization evidence.
- Resolve low-fit viewpoint, unreachablepose and directioncoverage with measured
  observation/planning improvements. Do not add trueposefallback or lowerfitgate.
- Camera actor still needs all-phase recovery before public integration. Then
  exercise full voice/chat/Stop/change/return journeys with visible provenance.
- Useful learning, camera-informed public operation, live/noise/audible/cold
  latency, concrete hardware adaptation and convincing human demo remain open.
  This failed learning slice is progress, not completion or a blocked audit.


D2c contract — future contact/release prediction:
- Previous goal turn is progress: D2b published fork9040de0/root11fd506,
  exactremote verified, bothclean at freshinspection;161lab/142fork tests pass.
- [O] Free-space estimate correction does not improve fulljourneys. [I] Predicting
  release consequences is the missing model capability, highconfidence; raw
  state-estimate RMSE is insufficient as physical utility evidence.
- [D] Frozen new72train/18validation/24test scenes before collection/fitting,
  balanced tool×journey, plus nine proposedXY offsets in[-20,0,20]mm².
  New10mm future-position validationp95 and10ms inference gates are provisional
  for a different future-outcome task; do not relabel D2b as passing them.
  All original physical thresholds and95%journey gate remain unchanged.
- Hypothesis: action-conditioned predicted final placement, height and neighbor
  disturbance can choose a better descent/release action than rigid placement.
  Compare against zero-offset, per-tool constant and linear learned baselines;
  train on separate episodes, retain rejected/zero-data trajectories, open test
  once after selecting on validation. Preserve D2/D2b regressions separately.
- Actor inputs: camera history and robot telemetry plus proposed action; label
  truth and exact snapshot branching only in the offline collector/verifier.
  No true-state runtime fallback, default-controller or microphone changes.
- Bounded2hypotheses max; first verify a repeated baseline branch reproduces
  the actual deterministic future, then collect/fit/judge. Replan on failures.
  Rollback publishedD2b. Full goal and publicA4workflow remain active.


D2c execution — future outcomes, October 11:
- Frozen114scene fixture7fda988b... before collection;72train/18validation/
  24test. Testlayouts nevercollected/opened. Nine±20mm/zero actions.
- Physical counterfactual collector keeps snapshots/truth outside actor.
  138release states/1242action outcomes; exact zero-action replay againstnormal
  continuation and repeatedbranch acrossallstates. Training1008rows/67of72
  scenes, validation234rows/16of18;7pre-release failures retained.
- Model76camera-history/robot/actionfeatures,3fixed-seed members9413parameters
  each; TorchCPU2.14.1,300epochs. Also toolmean andridge baselines. NumPyonly
  inference; no dependencies or microphone/camera scope expanded.
- Firstfit1.821s:RMSE4.523/p958.417mm oncoverage, oneunknownheadingstate
  withheld because trainingflagconstant1→normalized100. Changeddatahypothesis
  once to training-only signedheading dropout; validation/tests/labels/guard8/
  hyperparameters unchanged. Protocol d3145ee3..., fit2uses2016augmentedrows
  fromsame67scenes,3.072s. No thirdfit.
- Fit2futureXYall234valactions:rigid12.631mmRMSE,constant7.614,linear10.232,
  NN3.842/p957.905mm;zero withheld. Offlineactiongain3.676mm/fullcoverage
  passesnew10mmfuture-p95/10msinference judge. D2bfailedjudge unchanged.
  IndependentTorch/NumPy paritymax5.51e-9(1e-6numericbound).
- Native9actionprediction0.071/0.088msmedian/p95,first.132ms. ActualIK-filtered
  chooserincludingfeatures+kinematics5.17/11.55ms;camera/speech/motionexcluded.
- Full18valjourneys rigid16/18vsNN14/18. Initial16placementsallpass35mm;
  mean12.491→8.825mm, but2freshreturnsfail. Same2initialgeometricrefusals.
  BoundedIKcandidatefilter avoidschoosingunreachableposes but still14/18;
  modelnotpromoted.95%fulljourney/lift/grip/speed/4mmjudges unchanged.
- [O] Returnvalidation000 wristload−12Nm(normalized10.535) vsmean−.107,
  std1.129;actuatorsaturation and modelrefusal. Exactcontact/servo causeunknown.
- [O] Returnvalidation014 currentIKseedends109.645mmerrorafter120iters;
  home-seed scratchFKfinds.429mm/.000259radorientationerror. Poseisreachable;
  single-startsolver fails. No newIKmotionpolicyadopted/physicalprovenyet.
- Replan aftertwofits/twophysicalpolicies: missing verifiedmotion/tracking/
  recoverycapability and changedfuturegraspstates, notanotherblindfit.
  Preserve24unopenedtests fornextvalidatedpolicy. Fullgoal remainsactive.
- Fresh165labtests(4release-focused) pass;Ruff/format85files. Newanalytic
  exactzeroensemble-std assertion failed3.47e-18roundoff, correctedonlynumeric
  atol1e-15, physicalbounds unchanged. Exportedfork146tests/Ruff61filespass;
  all46pinnedupstreamhashes intact;publicappReady withoutmic/motion changes.
  Scientificfigure inspected; experimentalcheckpoint andhonestevidence retained.

Next active D2d — verified motion and recovery before camera integration:
- Implement bounded robot-only IKseed recovery from independently verifiedFK
  poses; preserve position/orientation tolerances, actualphysics and forcecaps.
  A mathematicalIKsolution doesnotprove a safecollision-free jointpath.
- Diagnose saturatedwrist/actualTCPtracking after transit, distinguishcontacts,
  jointlimits,servoerrors andsolverbranches. Observe robotmeasurements andhold
  onunverifiedmotion; neverextrapolateNNor wideninputbounds tohidefailure.
- Resolve cameraweakfits by measuredviewpoint/reobservation, notlowerfitgate.
  Complete all-phase cameraStop/resume/replan and independently observedrelease
  beforepubliccontrollerintegration. Preserve currentA4voiceworkflow.
- ReuseoldD2/D2b/validationcases asregressions; onlyopen24newtests aftera
  coherent full-loop policy passesvalidation. Learningmustimprovewholejourneys.
- Camera-informedpublicoperation, meaningfullearninggains,live/noise/audible/
  coldresponsiveness, hardwareadapter/plan andhumanlive demonstration stayopen.


D2d active contract — motion/perception recovery:
- Previous goal turn is progress: fork50d8c76/root9ad4c4e published and clean.
  Full goal still active; C3futuremodel offlinepasses but physical14/18vs16/18.
- [O] Baseline servo endpoints on3known journeys are~3.6–10.5mm TCP error,
  ~.007–.017rad orientation error. Saturatedwrist case has smallTCPerror5.49mm
  but−.109rad/s instantaneouswristvelocity/−12Nm; contacts show fingers/tool,
  no wrist/table/selfcollision at sampled endpoint. Exactcause stillunknown.
- [O] Wrench reobservation failures occur afterapproach; initialfits.896/.989
  pass. Atfailurebothfront/sideviews missing despite visibly exposedtool inarm
  shadow. Alternateview hypothesis rejected for these cases; brightness-dependent
  metalidentity is invalidated. Sidecamera stays optional/probe-only.
- [D] Hypothesis: normalized neutralcolor + unchangeddepth/geometry/ambiguity/
  fit.8 gate recovers shadows. Judge protectedD1clear72/occluded12 andactual
  reobservation, duplicates/coloredhandle/nondepth tests; no brightness fudge of
  source frames or trueposes. New source RGB is untouched.
- [D] Robot IK recovery uses boundedhome seed in a separateFKbuffer whencurrent
  seed fails; original.8mm/.008rad criteria, joint/forcecaps preserved. FKproof
  is not collision-free motionproof. Actualphysics/journeys independentlyjudge.
- [D] New tracking gate15mm TCP/.035rad orientation is provisional, based on
  normalobservedendpointdata, separate from unchanged35mmplacementcheck.
  Boundedsettling/hold onmiss, no pretending commandedpose was measured.
- Keep learned modelguard8 unchanged and record refusals. A separately tested
  conventional camera+trackedrobot plan may recover a refused model action;
  it must use observedrack/knowncatalog, never trueposefallback, and independently
  verifyplacement. Explicitly label such recovery, never claimNNconfidence.
- Freezepolicybefore24newC3tests; use18validationandoldD2/D2b regressions first.
  Attemptbudget2 perhypothesis; replanfromactualfailures. No thirdblindfit,
  gains/forcecaps/physicaljudges unchanged. PublicA4voice remainsready.

D2d execution — camera/motion recovery, October 11:
- [O] Final opt-in recovery profiles pass17/18 frozen validation journeys,
  12fresh-camera returns each. Conventional mean initial error12.261mm;
  same17 learned placements10.548mm. Remaining wrench redirect36.424mm
  exceeds unchanged35mm;95%whole-journey gate fails. No promotion.
- [O] Shadow-only neutral pass plus limited measured tilted-plane fitting
  preserves72/72 clear detections,p95.257mm,max.404mm;all12hiddenwithheld.
  Separate shadow pass avoids the rejected combined-mask regression71/72.
- [O] Bounded robot-only home IK + independent FK; actual endpoint motion
  verification with bounded settling/hold. Currentpose/forcecaps unchanged.
- [O] Wrist2ms trace alternates±12Nm127times/128samples,mean0Nm,
  netjointdrift1.433e-5rad/256ms. Earlier sustained-load interpretation invalid.
  No gain/force/inputguard change; diagnostic traces retained.
- [O] Catalog footprint clearance changes wrench orientation to avoid observed
  screwdriver overlap. Empty-hand survey + explicitly predicted stationary
  neighbor history solves occluded-neighbor planning, not fresh target sensing.
  History≤30simulationsec;uncertainty.5mm+.2mm/s is provisional/un-calibrated.
  Invalid/ambiguous/contradictory/neverobserved neighbors refuse; fresh target
  requires≤.25sec. No true object state or nominalrack fallback enters actor.
- [O] Release NN refuses deliberate reorientation as changed recipe; threelegs
  finallearnedrun use explicit conventionalfallback. Supported unsafe predicted
  futures cannot fallback. Existingweights/guard8/fit.8 thresholds preserved.
- [O] Stronger disturbance judge maxbody-centertranslation every32msframe
  acrossbothlegs, same4mm threshold; nottip/rotation/sub-frame collisionproof.
  Failedlinear-lift/centering/heldsurvey variants preserved; finalprofile omits.
- [O] Isolated30frame camera pipeline median77.245/p9582.512ms, first97.564ms;
  no motion/IPC/disk/speech included. Newfit modestly increases camera cost.
- All24C3test layouts stillunopened; D2/D2b legacyphysical sets not newlyrerun.
  Fullroot175tests passed before export, independentfork checks below.
  Scientificfigure inspected; publicA4 assistant unchanged; goalactive.

Next active D2e — changed-grasp evidence, then camera integration:
- Prediction: deliberate carry reorientation changes grasp/held-tool geometry;
  old release-model recipe cannot substantiate the remaining36.424mm redirect.
  Collect separate reoriented training/validation evidence or measure heldpose;
  judge full18journeys, then onlyopen24test after passing wholevalidation.
- Preserve35mmplacement/4mmneighbor/95%fullgate, inputguard8 and testfixtures.
  No blind residual offset or tolerance widening. Bounded2 hypotheses before
  replan. Camera actors must complete all-phase Stop/resume/replan before public
  integration, including failedgrasp/pregrasp; currentresume supports held only.
- Publicvoice/live/noise/audible/cold responsiveness, usefulmodel whole-loopgain,
  hardwareadapter/plan and convincinguserlive demonstration remain unfinished.

D2d publication checks: fresh native-access175lab/156forktests passed;
Ruff/format93lab/69forkfilespassed;46pinnedupstreamhashesintact. Restricted
CoreGraphics/IPC run failedenvironmentaccess, correctednative-accessrun passed
without changing/skipping tests. Final source/fixture/asset parity verified.

D2e active contract — held-pose measurement:
- Previous turn is progress: fork1c1f739/root98b4477 committed and verified.
- Hypothesis1: rigid grasp error grows during redirected/reoriented carry and
  descent; existing RGB-D may observe enough handle geometry to update heldpose.
  Judge synchronized saved RGB-D only, independent physics labels afterward;
  reject partial/ambiguous/noisy fits. No truepose runtime fallback.
- Diagnostic002 reproduces exact36.4239399mm failure. Rigid error15.632mm
  beforedescent/.232rad,33.564mm nearrelease while gap~43.49mm remainsclosed.
  Diagnostic001 incorrectly labeled transition frames/comparedunsolvedlayout
  ratherthansettledinitialposition; excluded from camera accuracy/effect claims.
- Action boundary: opt-in held observation fit with declared geometry + robot
  proximity gating, separate from protected tabletopdetector; freshcapture,
  independentaccuracy/coverage and full18physicsval before integration.
  Attemptbudget2, allthresholds/frozenfixtures preserved. Goal remainsactive.
- Held-face hypothesis1 complete-face fit: all12 airborne views (front+side)
  withheld, despite independently labeledvisiblehandle331–1101pixels. Hypothesis2
  RGB-D robustplane patchesnearTCP alsoall12withheld. No loweringgeometry/fit
  gates, no actorintegration; missing full-face observability remainsunresolved.
- Replan: changed-recipe action-conditioned outcomes instead of anotherimagefit.
  Recoverypilot validation016 nine±20mmbranches exactlymatchnormal/repeatedzero
  fullintegrationstate(0error). +20mmX yields~17–18mmfutureerror versus36.424mm
  zeroaction. This is measuredcounterfactualevidence, not a chosenliveoffset.
- Collect samefrozen72train/18val with finalD2drecovery recipe. Test24excluded;
  outcome-labelv2 strengthensfutureaddedneighborlabel tomaxevery32msreleaseframe.
  DefaultC3collectorrecipe/final-displacementlabels preserved. No trainingonval,
  no oldweight/guard changes. Physical snapshot reset remains collector-only.

D2e execution — held geometry and missing training exposure:
- Bothopticalhypotheses withheld12/12airborneframes ofoneknownscene; allthree
  syntheticcompletefaces fitwithin1.5mm, clipped/invalid/farrefuse. No actor
  measurementfeedback. Missing heldobservability unresolved; no thirdimagefit.
- Recoverydataset1314physicaloutcomes/146states:1044train/116states/70of72scenes,
  270validation/30states/all18. Allnormal/repeatedzero integrationstatesexact.
  Strengthened futurelabelmax32msrelease displacement, version2; no testsopened.
- FirstfixedCPUfit3.330s withsame76features/3x9413params/seeds300epochs and
  training-onlypreviousheadingdropout. NeuralfutureRMSE6.568mmp9511.109mm vs
  rigid14.001/constant9.277/linear22.688RMSE. All270covered;9batchinference
  median.075/p95.084ms. Failsunchanged10mmp95gate;selectedkindnone.
- Criticaldataevidence:116trainingstates contain0deliberateturns whilevalidation
  has3. Newmodel'srecipeversionstays0 and cannotauthorize reorientedrelease.
  Addedexplicitrecipeguards; oldv2weights unchanged and remainrestricted.
- Publishedreproducibledataset803c79fc..., rejectedv3model9ef61218..., labeled
  measurements/figures. No fulllearnedpolicytrial becauseofflinegatefails and
  relevanttrainingcoverageabsent. Wholevalidationsuccessgainnotclaimed.
- Frozennexttraining-onlyturnprotocol beforecollection; implementation/collection
  stillpending. Needbalancedturnexposureacrossall3tools, keepval/testunchanged,
  combineepisode-groupednewtrainwithoriginaldata. One remainingfitbefore replan.
- Fresh180lab/161forktests pass;98lab/74forkRuff/formatpass;46upstreamhashesintact.
  PublicA4Ready,VoiceON,micidle; no UIactions,permissions,physics/forcechanges.
  Fullgoalactive, all-phasecameraresume/publicintegration/hardware/live remainopen.

D2f active contract — training-only turn curriculum:
- Previous turn is progress: forkd100048/root4d4482e published and clean.
- Hypothesis: adding supported deliberate turns to training will cover changed
  held-geometry release states without using validation/test labels for fitting.
  Predicted: nonzero turn exposure for eachtool; fixedval270actions improve
  p95≤10mm withfullcoverage; then whole18journeys pass95% withallphysicsgates.
- Implement frozen yaw-cycleprotocol; training-only collector requests an exact
  supportedorientation after existing camera/geometry/IK gates. Unsupported
  requests refuse and remainrecorded. Defaultminimum-turnplanner is unchanged.
- Pilot oneknowntraincase for exactnormal/repeatedzero fullstate replay, then
  collectall72training scenes. Combine withpublished recoverydataset; validation
  arrays must be bitwise unchanged and train/test provenance checked before fit.
- Same76features/3fixedseeds/300epochs/headingdropout/guard8/.008std/20mmactions.
  One remainingfit before replan; no further blind fit ifcriterionfails. Requires
  actualturntrainingexposureinall3tools before recipe1authorization; tagalone
  isn't qualification. No publicapp changes andall24testlayouts remainunopened.

User steering — October 11, reuse existing robotics models and software:
- User challenges whether we are reinventing the wheel. Agreed: custom motion
  control has become too much of the critical path for the interactive assistant.
  Redirect active work toward existing pretrained policies and maintained motion
  libraries; preserve the full goal, honest physics judges and prior experiments.
- D2f local prototypes remain uncommitted/opt-in and are not exported or enabled
  in the public app. Two direct-turn training pilots yield0rows duegriploss.
  Staged fixed-waypoint turn refused joint-step bound; adaptive subdivision
  preserves0.04rad/0.8mm/0.008rad limits and improves mathematical continuation.
  Two native ±.25rad FK tests pass without realqpos/ctrlmutation. Full staged
  physicalvalidation17/18 stillfails95%; validation016 dropsheldwrench during
  transit afterturn. No new model fit, no fullcurriculumcollection, no promotion.
- Additional diagnostic refutes the suspected IK cause of validation016's
  orientation choice: exact intended inherited pose is supported by bothcurrent
  andhome scratch seeds (position.221/.189mm). Camera-derived planar clearance
  is3.866mm below required7mm; geometry margin, not missingIKseed, causes turn.
  Preserve clearance/physicalbounds; do not weaken them or patch a singlecase.
- Current primary sources checked: upstreamDum-E already integrates GR00TN1.7
  and offers SO101 fruit-picking checkpoint; this is not proven screwdriver skill.
  https://github.com/aaronsu11/Dum-E
  https://github.com/NVIDIA/Isaac-GR00T
- OpenPi provides pretrained pi0.5-LIBERO for existing Panda simulation and
  pi0.5-DROID for Franka tabletop operations; upstream explicitly warns that
  checkpoints may not transfer to another robot/setup. Tested platformUbuntu22.04,
  NVIDIAGPU inference >8GB. https://github.com/Physical-Intelligence/openpi
- SmolVLA is a pretrained450M foundation policy for LeRobot; official guide
  recommends task-specific fine-tuning and~50 demonstrations. Do not promise
  ready-made screwdriver behavior. https://huggingface.co/docs/lerobot/smolvla
- Established motion libraries include MoveIt2 and Drake; Drake publishes macOS
  Python wheels. Evaluate reuse/compatibility rather than more bespokeIK tuning.
  https://moveit.picknik.ai/ https://drake.mit.edu/pip.html
- Next R0: reproduce a pretrained policy in its existing supported simulator,
  establish baseline behavior/latency, then connect retained Dum-E voice/Stop
  layer and adapt ourworkbench. pi0.5-LIBERO is a concrete matched-Panda candidate;
  Linux/NVIDIA policy process belongs on existing5090 workstation when available,
  Mac remains voice/UI/simulation client wherever practical. Inspect workstation
  access/capabilities before any setup; no CUDA on Mac or new permissions/services.
  No more D2f sweeps or new custom dynamics fits as the primary critical path.
- Wholegoal stillactive: interactiveassistant+camera+recovery+usefullearning+
  hardwareplan+humanliveproof remain required. Reusing policies changes method,
  not completion criteria. Preserve all previous data/fixtures/failed evidence.

R0 active — official pretrained policy integration, October 11:
- Previous turn is progress: user-directed reuse pivot grounded in upstream docs,
  custom experiments preserved. This chat currently exposes only local projects
  and no remote shell; no ~/.ssh directory/config exists. Workstation access is
  unknown, not verified offline. Asked once for SSH/policy-server access; continue
  useful Mac-side work meanwhile. No remote task or new permissions created.
- Preserved10D2f prototype files + patch + hashes inresearch/turn-prototypes-20261011;
  restored published main implementation and kept all rawruns/ledger. No deletion
  of experiment evidence or default public workflow change.
- PinnedOpenPi commit215abfb217dbac7d5f1273282331b9b1866c0479. Use its official
  lightweightclient; no weights, GPU frameworks, submodules, or CUDA onMac.
- Compatibility: officialclient needsNumPy<2, lab needsNumPy>=2. Separate locked
  environment underintegrations/openpi-client avoids changing root/forkenv.
  StandardLIBERO camera/state/action adapter follows upstream example. Seven
  actioncolumns areOSCposecontroller inputs, NOT ourPanda's7jointpositions.
- Process-isolatedSDK connection avoids its unboundedretry/receive waits leaking
  into control. Generation gate flushes queued/late actions onStop/taskchange,
  boundedconnection/inferencefailure; remoteGPU computation itself is not cancelled.
  No nativeworkbench action mapping, simulatedpolicy or inferredmodel identity.
- Judge realofficialwire againstunmodifiedupstreamserver + explicitlysynthetic
  transportfixture. Tests prove connection/units/cancellation/errorhandling only;
  do not claim pretrainedpolicy inference, robot retrieval or closed-loop success.
- Next: inspect5090/driver/WSL availability viaread-onlypreflight, validatepinned
  runtimeBlackwell compatibility, reproducepi05-LIBERO benchmark, then connect
  voice/Stopandrenderer viaactualLIBEROadapter. Fullgoal andphysicscriteria unchanged.

R0 connection checkpoint — not pretrained robot behavior:
- Nine isolated tests pass against the pinned actual upstream SDK/server protocol.
  Invalid replies invalidate existing queued actions; a stalled SDK cannot block
  the observation deadline. Failed inference does not erase an observed handshake.
- 20 synthetic warm RPCs median/p95 0.637/0.802ms. Five Stop/local-request exits
  during300ms synthetic inference median/p95 21.375/21.872ms. Reconnect+next delayed
  reply median/p95 600.189/605.153ms; remote computation can continue.
- No weights loaded, no LIBERO rollouts, no policy-driven motion. Actual public
  app observed Ready, voice/listen-on, allthree tools onrack; default unchanged.
- See integrations/openpi-client/README.md and docs/pretrained-integration-audit.md.
  GPU access detail remains pending; continue with verified workstation once known.

R1 runtime preparation — supported Linux baseline, October 11:
- Previous goal turn is progress: actual official SDK/server tests and benchmark,
  isolated environment and authorized publication at6e001e0. Current repositories
  began clean. No pretrained inference or LIBERO rollout is claimed.
- Maintained LeRobot LIBERO guide requiresLinux. This Mac has no Docker/Podman/
  Colima/Lima command. Inspect exactOpenPi-pinned LIBERO f78abd68ee283de9f9be3c8f7e2a9ad60246e95c;
  do not install its oldCUDA trainingrecipe or inventaMacport. Simulator+policy
  baseline will run onLinux; Mac retainsvoice/UI.
- ActualOpenPi lock hasTorch2.7.1 withx86LinuxCUDA12.6.77, whileofficialBlackwell
  support usesCUDA12.8 builds. JAX0.5.3compatibility likewiseunverified. Do not
  blindly installthedefaultlock on5090 or claimGPUcompatibilityfromversions alone.
- Addedstandard-library host/runtimepreflight: noinstalls; optional30sGPUbf16
  kernel inexistingLinuxpolicyenv; CPUfallbackrejected; modelReadyalwaysfalse.
  ActualMac explicitJAXrequest exits1withheld beforeGPUimports; sourceaudit exact.
- Elevenisolatedtests pass, includingnonLinuxguard andnoinventoryreadinessclaim.
  ActualGPU/Linuxbranches unexecuted; workstationaccessquestionstillpending.
  See docs/pretrained-runtime-audit.md. No app/controller/microphone changes.

F preparation — hardware adaptation plan, October 11:
- Previous goal turn is progress: read-only runtime preflight implemented/tested
  and published at 4e47de8 with source/runtime evidence. Repositories began clean.
- Compiled current MuJoCo scene without rendering, stepping or hardware IO.
  Simulated masses: screwdriver 76 g, wrench 89 g, hammer 61 g. Catalog dimensions
  independently match compiled collision bounds; root/fork inventories agree.
  Handoff center is 0.660 m from base origin in XY. These authored facts cannot
  establish real-tool capacity or suitability of the layout for a compact arm.
- Prepared concrete plan for tool/layout measurements, reused LeRobot SO-101
  driver, explicit action units/embodiment, camera/time/gap calibration, staged
  offline/real evaluation and verified outcomes/Stop. No hardware operations.
  Generic adapter and real readiness remain unimplemented/unverified.
- Existing SO-101 connect calibrates/applies a gain preset; fixed reset/release
  poses are not read-only commissioning or validated tool skills. Future authorized
  integration must review these side effects rather than blindly call helpers.
- RTX access is missing for the third consecutive goal turn: refreshed projects
  show only local Mac execution projects; no SSH configuration directory or remote
  shell capability. One connection question remains pending. No GPU model job is
  running. This blocks the pretrained policy slice; the whole goal can be blocked
  only if no other meaningful work remains available.
- Re-probed the known long-idle local dialogue bottleneck: read-only understanding
  takes 27.386 s, then 1.113/1.115 s. First token 26.660 s, then 0.394/0.395 s;
  generation ~0.71 s each. Same job, no audio/speech/motion. Natural idle length
  is unknown; this is not a controlled cold-start distribution. Global swap usage
  before probing is 8324.56 MiB; paging causality is unproven.
- Concrete Mac-side progress remains possible: test the existing 9B MLX checkpoint
  against unchanged quality fixtures, sampler/prompt and promotion gates. Public
  metadata verified at 938d8919941c6e7efd3c7150eff7fe9d12afa631, weights 5.95 GB;
  anonymous data-only download started in exec session 46246 and observed live.
  Candidate not loaded or accepted; original default remains enabled. Keep the
  whole goal active for this responsiveness work. RTX access question is pending.

B5 — model selection and idle responsiveness, October 11–12:
- Previous turn is progress: verified inventory/plan publication at 9f77efe,
  actual 27.386 s idle response evidence, downloaded/publisher-verified 9B weights.
  Downloads and hash worker finished; do not restart those jobs.
- Sequential 9B native comparison: original 2/45 wrong (hammer falsely unavailable),
  context 0/18, pairs 1/36 wrong (unrequested Stop), quality schema 0/30. Actual
  reply review 27 complete/3 partial. Peak MLX 6.166 GB, but warm requests slower.
  Reject candidate; no prompt/gate changes or candidate speech/physical promotion.
- Inspected official MLX residency fix a59cc23190f1e26fabcba8693607bb4c34b2ac2b.
  Installed 0.32.3 lacks it. Separate build failed first on CMake PATH, then on
  missing xcrun metal even with CUDA OFF and supported Metal JIT ON. No wheel
  installed, no working dependency/system changes. Do not repeat without a new
  capability/hypothesis; preserve source/build logs under external/.cache.
- Supported-API 1 GiB mechanism probe: 12 s idle first sum 49.337 ms without
  maintenance, 15.807 ms with 1 s scalar work, 46.369 ms with 3 s work. One sample
  per setting, fixed order, not LLM proof. Process budget restored on cleanup.
- Added bounded process residency + independent scalar work while worker idle;
  requests/active inference take priority, no text generation/audio/task commands.
  MacOS 15+ automatic mode enables only with supported allocation budget; logs
  fallback reason, 0 opts out, 1 requires support. Requested budget 18.50 GiB;
  sampled tiny refresh ~0.2–0.7 ms. Power/heavy-app costs unmeasured.
- Actual accepted model after three ~12.3 s idles: off median/max 1.434/1.475 s,
  on 1.144/1.153 s. One 120.262 s idle answers correctly in 1.134 s. Not proof
  that the earlier unknown-duration 27 s stall, hours, sleep/wake or stress is solved.
  Off raw completion timestamp corrected by subtracting request duration; retained.
- Native 129/129 decisions and 30 reviewed replies pass within case contexts;
  early native timing overlapped lab checks (not clean causal timing). New-waveform
  speech pilot retained; primary reused actual responsiveness-fixtures-001 after
  other checks finish: 30/30; common median/p95 1.162/1.194 s; general 1.562/2.044;
  guards 1.569/2.054. Same old last-voiced-sample boundaries, no target lowering.
- Real saved Stop during pending inference reaches POST at588 ms, late reply
  superseded, grip retained, settled maximum joint drift0.000572 rad. Live mic and
  speakers disabled during automated motion; restore previous settings afterward.
- Final lab186/fork167 checks pass; Ruff/format pass. Explicit and automatic mode
  paths/fallbacks tested; actual default runtime observed Ready with budget enabled.
  Public default runtime exec58488, ports8766/8765/8001, logs
  Dum-E/extensions/workbench/runs/residency-default-ready-001. Old runtimes exited.
  Benchmarks/build/probe handles are terminal. Full goal still active; camera/VLA,
  long-idle/live/acoustic/audible proof and user demonstration remain incomplete.


B6 — reuse pretrained speech detection, October 12:
- Previous goal turn: no progress; its read-only confirmation did not change
  authoritative state or the next action. Revalidated current source/runtime. This turn
  tests and integrates Silero v5 through pinned browser VAD/ONNX packages.
  No custom manipulation work resumed; actual OpenPi/Linux GPU demo still awaits
  the outstanding workstation connection. No policy job is running remotely.
- Frozen 35-case saved PCM protocol SHA
  babe8ffd33c4e625c8d8a2aa3f91996f4aec573fe4ccbc5ecd9078d6e241c102.
  Energy gate13/35, two noise-only submissions; browser Silero35/35, zero.
  Model cached load79ms, inference p95~.20ms. Virtual time, not live latency.
- Actual AudioWorklet/recorder streams5/5; real local Whisper streams5/5.
  No actual mic/speakers/robot command. Noisy Stop callback561/696ms after
  clean voiced boundary; ordinary request1159/1433ms. Physical Stop not measured.
  Expected silence message was initially misjudged; retained original raw report,
  corrected only that judge and reran. Fixture/model/gates unchanged.
- Local-only checksum-verified assets, no npm install, no CUDA/cloud/new mic
  permissions or idle listening. Preload never acquires audio. Cancellation
  isolates frames and bounds initialization to5s; missing assets disable Speak.
- Lab187/fork168 regressions; recorder/adapter Node contracts and Ruff pass.
  Upstream46 hashes match; Python locks unchanged. Public runtime exec46066
  runs/silero-default-ready-001 independently observed Ready, Speak enabled,
  Voice/listen ON, microphone idle. Prior public runtime58488 exited normally.
- docs/speech-detector-audit.md + evidence retain exact scopes and failures.
  Real acoustics, natural pauses, physical/VLA work and human demo remain.
  Full goal active; this speech milestone is not completion.


B7 — recorded browser speech to native physical Stop, October 12:
- Previous goal turn: progress; Silero shipped/published at fork7c9c774 /
  lab8271aaa. Revalidated live exec46066 and clean current worktrees.
- Mac-only project inventory; no exposed workstation shell or policy server.
  OpenPi-supported model demo still awaits the existing unanswered access detail.
  No custom manipulation or dynamics sweep used as a substitute.
- Froze six retained Stop variants plus an actual saved question before execution.
  ProtocolSHA cd330c59d168e8d183f99b20287bc15ae5387567c2a2695a5d19ee92f6435c82.
  Actual browser MediaRecorder/AudioWorklet + Silero + Whisper + conversation
  model + unchanged task bus + MuJoCo; no mic/speakers/hardware/mocked model.
- Browser6/6; independent native event/physical judge6/6, all six interrupted
  actual ongoing token generation and superseded the late reply. Native Stop
  median613ms / samplep95722ms / max723ms from retained voiced boundary.
  Gripper retained, elevated tool, cancelled tasks, no queued work, tracks ended,
  unrelated tool center displacement <4mm. Residual joint drift .004563–.009253
  rad over600ms after Stopped flag; <.02gate. Settling duration still unmeasured.
- Independent judge reconstructs frozen timing, validates exact model/native
  event identities;15 retained-run alterations confirm meaningful rejection.
  Published source/locks unchanged; only verification tools/docs/protocol added.
  No need to repeat the prior187/168 application regressions for test-only edits.
- Simulator exec46066 remains Ready; Voice/listen restored ON, mic idle, tools
  reset; cancelled test tasks retained. Close temporary judge tab/server afterward.
  Full goal active; trained arm control, camera journey failures, acoustics, audible
  responsiveness and human live demonstration remain incomplete.


B8 — critical-path access audit, October 12:
- Previous goal turn: progress; full browser/models/task-bus/native-physics Stop
  qualification published at fork ae0a729 / lab bf3723a. No functional change
  or new policy result is claimed by this read-only access audit.
- Revalidated clean checkouts, public runtime exec46066 live and Ready, tools
  on rack, Voice/listen ON, microphone idle. No trained-policy process runs
  remotely; the local simulator is left available.
- Available project inventory still exposes only local Mac projects. No local
  SSH configuration/connection exists; available tools expose no remote shell
  for this workspace. Native desktop surfaces cannot currently be inspected
  because the Mac is locked; browser access remains available. This is not
  evidence that the Windows PC lacks remote access, only that this chat has
  no usable route to it yet. No unknown hosts scanned or credentials changed.
- The same missing workstation connection has persisted through R0/R1 and
  B5/B6/B7. Useful Mac-side speech work was completed while it remained open.
  The next major requested result is actual pretrained manipulation in its
  supported Linux/NVIDIA simulator, followed by adaptation to Dum-E. No
  unsupported Mac port, extra custom controller or unrelated benchmark will
  substitute for that result. The overall goal is not achieved.
- Mark goal blocked on workstation access rather than keep automatic work
  cycling through small side tasks. A concise access/setup question is pending.
  Resume with the existing read-only Windows/Linux preflight, verify installed
  WSL/Linux, driver and Blackwell-compatible GPU backend, then load the pinned
  policy and record actual supported rollouts/success/video/timings.
- Existing live-room/human demonstration, camera/manipulation failures and
  precise mechanical settling duration remain incomplete. Full objective,
  physical gates and authorization boundaries are preserved.


B14 — faster Bonsai load configuration, October 12:
- Previous goal turn: progress; fresh 15-case evidence revealed current median
  2.061 s rather than assuming the older 0.510 s measurement still applied.
  Current source, runtime and linked-device placement were revalidated.
- Baseline median HTTP/native overhead ~3 ms; model inference dominated. Reloaded
  only Bonsai on the existing linked workstation with explicit max GPU offload,
  one prediction slot and the unchanged 8192-token context/API identifier.
  Vision model remained loaded; no code, prompts, physics or dependencies changed.
- Same frozen 15-case sample: 15/15 correct before and after, median2.061→.686 s,
  samplep95/max2.891→.788 s. Both load settings changed together; sequential
  before/after samples do not isolate their individual effects or host contention.
- All four frozen dialogue suites ×3:129/129 decisions, median662ms/p95793ms,
  max901ms. Lead review30 factual replies passes existing criteria; repetitive
  feelings wording remains. Three12s idle replies815/839/1055ms, all correct.
  These are text timings, not live speech/audible/long-idle proof.
- Actual saved synthesized speech→Whisper→Bonsai→Dum-E→MuJoCo retrieval/return
  passes:145ms recognition,572ms native decision,208.4mm lift,9.69mm handoff,
  12.70mm return. Camera still identifies3tools via2views in2.617s, above2s target.
  Existing20 LM Studio/cache regressions pass; no fresh Stop/hold claim this turn.
- Reproduction/rollback documented. Explicit load has no TTL; remains resident
  until unloaded or device/app shutdown. Future default reload may restore slow
  settings; server configuration is not silently rewritten by the assistant.
- Real browser spanner question answers correctly without a job. Final8766 app
  Ready, all tools rack, Voice/listenON, micidle. Reusable matched timing plot,
  retained evidence and documentation added to authorized fork export.
- Full goal active: actual pretrained manipulation, camera-derived motion,
  room/acoustic/audible evidence and convincing human demonstration incomplete.


B15 — camera-motion requalification and shared hold, October 12:
- Previous goal turn: progress; faster Bonsai load qualified/published at
  lab5f70eee/forkc4e6820. Revalidated clean repos and public Ready/Bonsai/Gemma/v2
  session before offline camera work. No public task or microphone was started.
- Earlier conventional v2 run is terminal:17/18, validation016 wrench36.667mm
  outside35mm gate. Reused the existing optional straight-lift/centering profile,
  with no solver/trajectory/model/physics changes:18/18 under current contacts.
- Frozen32simsecond held-camera protocol SHA
  02ce28490d678acf402b7434a4e32854403939956ea101216f659ab3d1fc5d17:
  old position-only hold4/6, hammer minimum126.80mm below130mm retained gate;
  existing shared gravity-feedforward hold6/6. SimRobot now delegates to that
  method. No body freeze, weld, force/gain/friction change or learned weights.
- Actual adapter6/6 long-hold continuations; minimum130.09mm (narrow margin),
  maxjointdrift.00955rad, maxheldtranslation2.05mm; all physical placements<35mm,
  unrelated centers<4mm. Offline simulation clocks, not wall/spoken Stop proof.
- Final source/profile frozen before reserved test:18/18 validation,12returns;
  first24reserved layouts22/24,17returns, FAIL unchanged95% fulljourney gate.
  test009 screwdriver abstains atfit.7980<.8; test016 wrench loses encoder grip
  indication during lift before planned Stop. No test-layout tuning or gate change.
- Independent metric reconstruction matches all recorded verdicts; successful
  actor legs/returns are released_unverified, separate physics judge proves place.
  Three validation000 phase probes confirm resume unsupported during approach,
  grasping and withdrawal. All-phase recovery remains incomplete.
- Root269/fork250 regression suites,22focused camera tests and changed-file Ruff/
  format checks pass. Upstream46 hashes preserved. Camera remains experimental,
  not promoted to main. Raw frames/logs local; curated evidence/plot/protocol and
  verified one-method hold correction exported for authorized fork publication.
- Next major control path remains actual pretrained OpenPi/LIBERO in supported
  workstation runtime; WSL/Ubuntu information still pending. No pretrained policy
  inference/rollout, public camera motion or full-goal completion claimed.


B16 — bounded camera-response alternatives and access audit, October 12:
- Previous goal turn: progress; shared camera hold and honest22/24 reserved
  rejection published at lab56a3d8c/fork27872bb. Revalidated clean source and
  online preferred workstation. Registered development projects still Mac-only;
  no supplied PC shell/policy endpoint. Existing Ubuntu/WSL question pending.
- Tested one request containing two synthetic views with strict single-view
  output. Frozen2pilots accurate2/2, zero absent false positives; all-tools2426ms
  misses unchanged2000ms target (empty1469ms). No app integration/validation run.
- Bounded second hypothesis: already-cached MacGemma12 with explicitmaxGPU,
  4096context/single slot. Memory87%free, estimate7.88GiB, load2.83s. Same2pilots
  accurate but5232ms/all-tools and5737ms/empty total fail target. Temporary alias
  unloaded; no download or preferred-device/main-instance change.
- Existing remoteBonsai/Gemma retained. No application/physics/control/prompt
  change, no new real mic/camera or policy execution. No full regression repeat
  for evidence-only work; prior269/250 result covers unchanged application.
- Official remote CLI docs and installed help inspected: existing app-server
  endpoint needed; none supplied. No server/pairing/security change started.
- Negative findings close the2attempt latency slice and change the next action
  to obtaining real workstation/Linux readiness and execution access. Do not
  claim a policy job is running, verified waiting, camera promotion or completion.
  Full goal remains active; no further speculative model/view/IK tuning this slice.

B17 — Windows migration, measured GPU speech and actual pretrained rollouts, October 12:
- Adopted the user's PC-only sustained mandate. Windows11Pro ~192GiB RAM,
  RTX5090 32607MiB/driver616.92; existing Ubuntu24.04.3 WSL2 with94GiB RAM.
  Fork31cd447 verified before cloning; unrelated Unity checkout preserved.
  No lab bundle needed and no Mac environment/runtime used.
- Rebuilt extension from its lock. Replaced Linux MLX ASR with pinned local
  faster-whisper small.en, and Mac output with installed local browser voices.
  Mic listening starts off; Stop/mute/page departure reject late speech, and
  playback errors remain visible. Windows launcher verified, ports8875/8876/8801.
- Initial suite during package copying was invalid evidence, not a baseline.
  Windows CRLF conversions restored only when protected hashes match. All46
  upstream hashes pass; no physics/controller/placement/lift criteria changed.
  Final251-test suite passes; native echo regression found/fixed; JS checks pass.
- Complete typed, CPU saved-speech and CUDA saved-speech interaction judges pass:
  real lift/place, conversation/change, old-tool return, Stop/resume/contextual
  return, withdrawal and clarification across completion. User live mic remains
  untested. Chrome renders the real scene; David/Mark/Zira voices and capture APIs
  present. Forty-five-second native video180frames; raw audio synthetic/local.
- CPU30/30 phrases correct: cold1601ms, warm median/p95 829/909ms. CUDAFP16
  own locked libraries30/30: first10102ms, warm187/209ms. Cache-library6/6
  warm173/178ms, first12346ms. Driver cache/cold and GPU contention limits retained;
  no CPU fallback. Readiness exercises actual GPU speech before enabling Speak.
- SavedStop CPU clip-ready→cancel789ms; CUDA274ms; each n1 excludes capture/pause.
  Separate2-second hold traces max tool drift .452/.778mm and joint range
  .000135/.00794rad, with verified resume/return. Different stop poses, not a
  hold-profile comparison. Full spoken-word/ack/acoustic timing remains open.
- Local Bonsai fixed15-case text check15/15, median/p95 617/778ms. Camera smoke
  after restoring Local Gemma needed two views1331+1056ms; last-view latency
  alone is not full response. Existing22/24 camera-motion rejection preserved.
- Official OpenPi215abfb/LIBEROf78abd6 sources/locks inspected. Huge Windows-mount
  environment copy replaced by cached native-Linux hardlinks. JAX0.5.3 actual
  GPU bf16 kernel PASS; pinned Torch2.7.1/cu126 kernel FAIL sm120, preserved.
  Policy stayed JAX GPU; separate Py3.8 simulator explicitly uses CPU Torch support.
- Recorded/verified16 GCS objects12,439,085,481bytes with immutable generations,
  CRC32C and external SHA256 notes. Old EGL build fixed via existing CMake and
  documented policy-minimum3.5, no simulator source edit. Actual two-camera RGB
  render and OSC_POSE contract verified; never mapped seven outputs to joints.
- Frozen before inference: LIBERO spatial0/1/2, init0, seed7, replan5, original
  220-step limit. Real pi0.5-LIBERO checkpoint3/3 simulator successes in
  103/110/134steps, saved videos/actions. Load17.453s; first inference31.169s;
  69 warm calls median/p95 106.577/127.382ms. These are three supported bowl/plate
  layouts, not workshop generalization or broad benchmark-rate qualification.
- Policy server forced GPU and loopback, then stopped after bounded evaluation.
  Local Gemma alias restored; LM Studio confirms both models Local. Public app
  remains scripted. Source, simulator lock, frozen protocol and curated evidence
  reviewable; recordings, weights and raw logs stay ignored/local.
- Next: actual-policy voice selection and Stop at LIBERO execution boundary using
  existing cancellable client, prewarm before ready, preserve stale-chunk rejection
  and measure physical holding/recovery. Then held-out workbench camera/adaptation
  gates and live user-controlled microphone demo. Full goal remains active.
  Reproduction/details: windows-migration.md and windows-migration-evidence.json.

## B18 — PC actual-policy voice interruption, experimental (2026-10-12)

- Baseline e8e116d. Hypothesis: existing cancellable OpenPi client plus local
  voice/catalog selection, direct physics Stop, real gravity hold and new-camera
  replan on resume. Gates fixed before trials; no main tool controller change.
- Actual pinned GPU pi0.5-LIBERO prewarmed on a real saved observation before
  readiness. Ten predictions discarded, one explicit RNG draw. Continuous RNG
  across trials; none reset on Stop/resume. No CPU policy fallback.
- Separate loopback Panda lab uses native OSC policy actions and original task
  success predicate. Inference gaps use neutral native OSC. Explicit pauses use
  native joint servo kp300/damping2 and unchanged torque caps, observed inside
  the torque callback. No policy vector is interpreted as joint angles.
- Preserved native/captured OSC, joint damping, timing and dialogue failures.
  Strategy changed after repeated failures. Evaluator sensors now refresh at
  native control rate; Stop captures the measurement origin and its age. No
  object pose/velocity edits, welds, frozen objects or scene reset on resume.
- Frozen tasks0/1/2: **2/3 complete live sequences qualify; lab not promoted**.
  Task0 reached native success but lacked an observed >=80mm two-finger-contact
  Stop trigger. Task1/2 hold drift .661/1.432mm, joint excursion .00358/.01639rad,
  minimum lift97.3/87.9mm, contacts retained; physics advanced1.036/1.012s over
  2.342/2.374wall seconds. Stale epochs rejected, same-episode real-policy resume
  reached native success in114/90 actions,157/122 active steps (limit220).
- Saved synthetic Stop235.3/227.9ms clip-available to response; direct cancel
  1.51/2.20ms (two samples, excludes microphone/pause/audible onset). A real late
  task2 inference chunk was rejected. Native success had grip still closed;
  delivered-object release remains unqualified.
- Separate gravity witness passed: finger opening caused80.70mm bowl drop and
  loss of contact while paused, without advancing policy action count. This extra
  episode is outside the fixed three-task denominator. Raw camera/audio/actions/
  logs/models remain ignored and local.
- Windows policy launcher verified actualGPU warmup/readiness, bounded shutdown
  and automatic local vision restoration; only owned lab processes stopped.
  Camera assistance is temporarily unavailable during this GPU lab. Workbench
  voice/tools remain available. Restored actual camera answer functional,2.749s
  HTTP wall; task state unchanged. Both LM Studio models Local again.
- Validation:251 workbench tests +22 transport/coordinator tests;46/46 protected
  upstream hashes; changed-file lint/format, browser module syntax, local speech
  cancellation and shell/PowerShell syntax pass. Microphone never activated.
- Continue task0 contact diagnostics/new explicit policy qualification, held-out
  camera/adaptation work (previous22/24 still rejected), and user-controlled live
  microphone verification. Goal remains active. Details: libero-live-pc.md and
  libero-live-pc-evidence.json.

## B19 — prospective PC camera cohort rejects target-only coverage (2026-10-12)

- Baseline03981be, local WSL Python3.12.3/MuJoCo3.15.0/NumPy2.5.4. Canonical
  frozen fixture hash verified after restoring only proven CRLF conversion.
  Existing camera profile18/18 validation and6/6 long-held continuations reproduce
  on PC; hammer held-height margin remains only .089mm above130mm.
- Bounded hypothesis: one calibrated side-view retry after target observation
  refusal, opt-in only. Same .8 fit/freshness/volume gate; no nominal pose fallback,
  controller/physics/force/model change. Real rendered recovery with tool truth
  denied passes; two invalid views or absent calibration refuse without physics
  advance. Existing gravity hold remains active on failure.
- Complete-journey judge now also requires finished release/withdrawal and
  measured open fingers. Placement35mm/lift80mm/rest/disturbance gates unchanged.
  Candidate18/18 validation. Sources/judge/runtime/recipe frozen before sampling.
- Prospective training-distribution recipe seed2026101301 generated54 cases,
  six per tool/journey pair, no filtering/resampling. FixtureSHA76b98a4134055633
  edf0c0d02dff157af790cd8f193a61492f64897aed603b6e. Full51/54 (94.44%) **FAIL**
  against unchanged95% gate; first-leg physical53/54 is not substituted. All54
  verdicts independently reconstructed; Wilson95% interval84.89–98.09%.
- Alternate target views selected0: no coverage gain established. Two screwdriver
  returns stop at ambiguous neighboring wrench (000/027); wrench redirect052
  loses grip indication,255.78mm high/.978m/s despite31.43mm XY error. Failures
  retained. New54 and old24 are now evaluated evidence, not future unseen tests.
- Full254 tests pass;46/46 protected source hashes; changed-file lint/format pass.
  Public camera motion remains unpromoted. Raw rendered data/logs stay local.
- Next strategy: complete-scene optical recovery under unchanged neighbor/fit/
  clearance gates, then a new frozen prospective cohort. Preserve separate grip
  failure; no physics or IK sweep. All-phase recovery/task-layer integration and
  user-controlled live mic verification remain required. Goal active.
  Details: camera-multiview-pc.md and camera-multiview-pc-evidence.json.

## B20 — complete-scene optical recovery and grasp-state diagnosis (2026-10-12)

- Baseline5aafd82. Bounded change: opt-in complete alternate scene on primary
  neighboring observation failure, with unchanged fit/freshness/clearance/cache
  bounds. Require all neighbors from one selected frame; ambiguous identity is
  never replaced by cache or a partial-view merge. Defaults remain off.
- Validation18/18,12 returns,7 selected side scenes. Three new scene guards pass.
  Frozen sources/runtime/recipe before new seed2026101302 generated54 balanced
  cases, fixtureSHAd2de78089c7f1d886f5c67a2d4453c715b900cd85cd855f223231923a47bd9e8.
- Prospective **50/54 complete journeys (92.59%) FAIL unchanged95% gate**;52/54
  first-leg physical placements not substituted.34 return attempts,8 selected
  side scenes,1 side target. All54 verdicts independently reconstructed. Wilson
  interval82.45–97.08%; no causal rate comparison with different-seed51/54.
- Failures retained:000 return grip loss(.947m/s,162.84mm high);009 ambiguous
  wrench neighbor/return held high;014 hammer lift branch guard;029 hammer weak
  observation/no pickup. No solver, physics, force/gain/model/threshold changes.
- After two failed optical cohorts, switch strategy. Posthoc four-case replay
  denies tool truth to actor, labels only evaluator. Rigid center error76.70mm;
  still56.75mm with supported23.36mm jaw gap during descent. Successful/failing
  peak joint speeds1.111/1.119rad/s do not establish speed causation. Closed gap
  does not establish held pose; no new optical, IK or physics sweep proposed.
- Earlier held fits already reject12/12 views; reuse that evidence. Prepared
  reorientation curriculum remains next substantive research action. PC dataset
  preflight:hash verified,1314x76,1044train/270val/0test,disjoint scenes,0 deliberate
  training turns. Existing pinned Torch2.7.1 CPU forward/backward works; no model
  trained or policy CPU fallback. Remaining bounded fit budget stays1.
- 257 full tests pass,46/46 protected hashes. Read-only hardware geometry inventory
  recompiles identically on PC; no hardware IO/simulation step. Hardware plan now
  records actual PC policy baseline instead of pending workstation access.
- Public camera motion remains unpromoted. All-phase recovery, task-layer camera,
  responsive live voice and user demonstration remain incomplete; goal active.
  Details: camera-scene-pc.md and camera-scene-pc-evidence.json. Raw data local.

## B21 — missing reorientation exposure collected; bounded fit rejected (2026-10-12)

- Baselinec9771e9. Implemented frozen training-only cardinal-yaw curriculum,
  defaultNone. Requested orientation must meet original scene/clearance/IK gates;
  no alternate-orientation fallback. Seven new guards; physics/solver/forces/gains
  unchanged. Pilot6 release states exact, fourth scene refused grip loss.
- Full90 non-test scenes processed:127 states/1143 rows,873train/270val,
  97 reorientation training states,74 commanded turns>.035rad.12 refused legs
  retained. All127 normal/repeated zero integration states match exactly.
- Historical validation audit fails(feature difference17.8435/label~19.986mm).
  No tolerance lowered: current-PC no-curriculum validation baseline collected,
  all270 rows feature/label maximum difference0. Splits disjoint, test0. Dataset
  SHA f8af4801771bc06c7499890704e89891f132c061b8d928bc18887278311bbfb9.
- Single remaining fixedCPUfit consumed:76features/3x9413params/300epochs/seeds
  unchanged, training-only heading-dropout873->1746 rows,30 validation groups.
  CPU Torch2.7.1 actual5.261s. No policy CPU fallback or new dependency.
- **No predictor selected.** Neural coveredRMSE14.02mm/p9522.15mm,76/270withheld,
  selectioncoverage60%,eligible gain-3.90mm. Same-coverage rigidRMSE13.85mm.
  Batch9 median/p95 .174/.201ms doesn't rescue failed gates. Feature guard rejects0
  rows; uncertainty withholding retained. Mean/linear also fail. No guard widening.
- Remaining fit budget0, frozen originalprotocol preserves preregistration1.
  Historical11.109mm vsnew22.145mm not causal due different validation trajectories.
  Curriculum supplied cardinal experience but may omit inherited distribution;
  no refit/sweep to test that within consumed budget. No deployed weights changed.
- 264 regression tests pass,46 protected hashes,changed-file checks. Public camera
  remains unpromoted. Next strategy: closed-loop grasp-state/motion evidence and
  all-phase recovery; no more optical/outcome-fit sweeps. Full goal active.
  Evidence/details: release-curriculum-pc.md/release-curriculum-pc-evidence.json.

## B22 — phase-specific interruption recovery, still experimental (2026-10-12)
- Previous bounded outcome fit rejected; fit budget remains zero. Changed
  strategy to task recovery using existing camera and robot ports.
- Frozen three-known-layout/nine-phase/32-simulation-second protocol baseline
  9/27 full journeys. Optional `phase_recovery=True` rescans before pickup,
  opens interrupted tabletop grasps before rescanning, and continues planned
  release/withdrawal. Held motion retains its original supported-grip gate.
  Default remains off; no public camera promotion, pose writes or physics changes.
- First evaluated recovery 25/27; hammer lowering/grasping interruptions fail.
  After two similar failures investigated, rather than widened guards/retried
  an optimizer. Empty-hand retraction succeeds; fresh pickup lifting hits the
  original 0.075-rad waypoint limit: fifth-joint deltas .0843505/.0750659 rad.
  Post-hoc robot-only diagnostic leaves qpos/qvel/controls exactly unchanged.
  A guard refusal does not establish a mathematical IK branch jump.
- Same physical lift80mm/placement35mm/open-hand/release/withdrawal/resting and
  unrelated-tool judges retained. Actor denied object-truth methods. Existing
  six long-hold/continuation cases pass6/6, minimum hammer height130.089mm still
  narrow. Review closes terminal-task resurrection via Stop; regression guard
  tests added. Final reviewed-source replay reproduces25/27; all273 regression
  tests pass,46 protected upstream hashes unchanged. Evidence JSON records hashes.
- No live mic or hardware actions. Human demo and complete latency remain
  outstanding. Next: continuity-aware motion planning with swept clearance
  and complete pickup/release evaluation, not more held-pose/network fits.
  Details/evidence: camera-phase-recovery-pc.md/camera-phase-recovery-pc-evidence.json.

## B23 — finer lift sampling executes; physical placement still fails (2026-10-12)
- Previous turn progress: published56a6adf 25/27 recovery. Read-only probe of
  the two known hammer lift refusals confirms fixed2x sampling reduces maximum
  joint steps to .059909/.044335rad under unchanged.075 guard, no state edits.
- Optional robot refinement tries original/2x/4x only on solved-step discontinuity,
  additional retries capped400waypoints. Other IK failure propagates. Actor
  executes all finer waypoints over the longer duration; default remains off.
- Same frozen nine-phase/three-known-layout full physical evaluation still25/27.
  Exactly2 refinements double44/43 to88/86. Actor completion27/27 does not override
  independent judge: two hammer placements36.334/35.601mm fail35mm, despite
  physical lifts244.854/241.305mm, open hand, resting tool and unrelated stability.
- Two similar placement failures prompt independent diagnosis: rigid estimated
  center error8.2mm after lift,12mm after transport,~30mm during placing, despite
  43.5mm gripper gap. Most error is pre-release; settling adds~1.1mm. No truth
  fed to actor or learned correction. Model-fit budget remains0.
- All277 regression tests pass, original long-hold6/6,46 protected hashes unchanged;
  results/source hashes in cartesian-refinement-pc-evidence.json.
  Public camera not promoted, full goal active. Next: supported-tabletop fresh
  camera verification after withdrawal and bounded physical placement correction,
  with prospective complete journeys. No more held-pose/outcome-fit sweeps.

## B24 — camera checks/corrects resting placement; prospective qualification fails (2026-10-12)
- Previous8f371bc progress: two formerly refused pickups now release but miss
  placement35mm. Read-only fresh postrelease RGB-D probe errors.0565/.0937mm,
  scores.9989/.9923, simulator state unchanged.
- Optional verify_release requires existing safehandoff/verifiedmotion: after
  withdrawal reobserve,<=25mm visual margin,25–80mm permits one fresh physical
  pickup to unchanged target, otherwise refuse. Fresh observation after second
  release mandatory; no second correction. Original rack preserved, defaults off.
  No pose edits/models; actor still released_unverified, physical judge separate.
- Same nine-phase/three-known-layout32sec protocol now27/27 (baseline25/27);
  only two hammer corrections, final9.590/9.720mm. Validation, not unseen/livevoice.
- Freeze before new seed2026101303 all54 cohort: full51/54=94.44% FAIL95;
  first-leg physical52/54,34returns,9side-scene views,0alternate target views;
  one return correction,0first-leg corrections. Independent54/54 reconstruction
  matches; Wilson84.89–98.09%. Snapshot unchanged after run. Different seeds
  mean no causal comparison against earlier50/54 or51/54. All failures retained.
- 005hammer rests within30.254mm but both camera views reject, no false verification.
 025/046wrench loses grip high/.840 or1.217m/s. Independent contact traces show
  no contact while gap proxy stillpasses, then guard trips up to96ms later.
  No privileged contact data fed to actor. Investigate temporal proprioceptive
  grasp monitoring next; do not simply weaken guards or repeat network fits.
- All280 tests pass,46 upstream hashes, originallonghold6/6; stale/missingcamera
  real-physics tests refuse additional pickup without advancing physics.
  Public camera still unpromoted, model fit budget0, full goal remains active.
  Details/evidence: camera-release-correction-pc.md/camera-release-correction-pc-evidence.json.

## B25 — grip recovery prototype and Odyssey-3 assessment (2026-10-13)
- Published baseline1c77eab remains authoritative. Fixed2mm per-frame gap-shrink
  brake on evaluated025/046 stabilizes joints but does not retain either tool
  over32s; they fall naturally. No held-object freeze or proxy success claimed.
- Experimental recover_grip flag: cancel carry,3.2s gravity hold, require closed
  empty-gap indication plus fresh supported-tabletop camera, open/reacquire once.
  First retrospective same54 replay50/54 versusbaseline51/54;025 recovered,
  046 camera-refuses,001/049 conservatively refuse a still-possible tabletop grasp.
  Known nine-phase validation27/27,284 tests, original longhold6/6,46 upstream hashes.
  Prototype remains uncommitted/unpromoted pending investigation, no threshold widening.
- User steering: research Odyssey-3. Primary launch/robotics/SDK/docs/model-hub
  sources reviewed. Recovery-policy representation/action decoder is relevant;
  public preview is not verified arm-control access. Docs still name2Pro, public
  hub has kernel packages, no verified3 checkpoint/5090 deployment recipe.
  Saved odyssey-3-assessment.md with access questions and guarded evaluation plan.
  No accounts, external messages, paid calls, uploads, installations or hardware.
  Goal remains active; research does not replace independent physical qualification.

## B26 — camera candidate meets prospective observed gate (2026-10-13)
- Previous turn progress: Odyssey-3 assessment1243f8b; gap prototype remained
  rejected/unpromoted50/54. Revalidated worktree and authoritative measurements.
- Investigated two similar001/049 refusals: gap shrinks during tabletop contact
  settling;001 retains table/both-finger contact. Keep2mm trigger, apply extra
  shrink check only with before/after TCP>100mm; original binary grip gate remains
  everywhere. No widening of placement/grip success limits or new model fit.
- Optional recover_grip: cancel carry, original gravity hold3.2s, require finite
  closed empty-gap proxy<15mm + fresh supported-tabletop camera, open/reacquire
  once to unchanged destination/rack. Uncertain hand or second loss refuses.
- Same previously evaluated54 improves to52/54 versuspublished51 andfirstproto50;
 025redirect completes22.148mm,046camera-refuses,005postrelease-camera-refuses.
  Independent54/54 reconstruction. Inheritedsplitheldout does not make replay unseen.
- Final candidate frozen before seed2026101304 all54: full53/54=98.15% meets
  observed95gate, firstphysical54/54,36returns,7side-scene views,0alttarget;
  one first-leg correction. Independent54/54 verdicts match; Wilson90.23–99.67%.
  Snapshot unchanged, all failures retained. No causal different-seed rate claim.
- New cohort has0grip-loss/reacquisition events: positive recovery evidence is
  known025 replay, not unseen recovery qualification. Remaining003return ambiguity
  leaves held screwdriver; independent32s hold joint.000102rad/tool.304mm/
  minheight215.90mm/bothcontacts retained passes; return remains failed.
- Known phase27/27, originallonghold6/6,287tests,46protectedhashes. Defaultsoff;
  candidate is not yet live/public. Next test Stop/resume inside new recovery
  subphases, then wire opt-in camera interaction and measure actual user journeys.
  Goal active, fit budgets0, no mic/cloud/hardware actions. Details/evidence:
  camera-grip-recovery-pc.md/camera-grip-recovery-pc-evidence.json.

## B27 — interrupted grip recovery preserves its existing sequence (2026-10-13)
- Previous81d44bd progress: prospective camera53/54, new recovery subphase Stop
  incomplete. Frozen known025loss/redirect four-phase protocol baseline1/4;
  settling incorrectly demands a held grip, opening/retraction unsupported.
- Bounded resume route recognizes owned counter1 recovery, retains original
  generator/rack/target/budget. Settling finite closed-command gap, opening
  finite/open-command/noncarrying, retraction/survey confirmed open hand required.
  Review adds nonfinite opening refusal. Ordinary held-grip gate unchanged.
- Final-source four32s Stop/physical return journeys4/4, rack22.15–22.45mm,
  maxjointdrift<.000140rad, grippercommand retained, reacquisitions always1.
  Lost tool may fall naturally; no claim of supported-tool retention or freeze.
  Fresh tabletop camera before pickup;80mm/35mm/resting/open/unrelated limits intact.
- Final294 regressions,46 protected hashes. Earlier original27 phases27/27 and
  longhold6/6 remain; final four cases and already evaluated54cohort repeated after
  finite guard:53/54, independent54/54 verdict matches. No fresh unseen claim.
- Inspected actual application contract: adapter needs controller metadata,
  separate evaluator, camera-only routing/context and cancellation before motion.
  Next wire opt-in live camera interaction and measure full natural journeys;
  defaults off, voice/human demonstration outstanding, goal active, fitbudgets0.
  Details/evidence: grip-recovery-interruptions-pc.md/grip-recovery-interruptions-pc-evidence.json.

## B28 — camera candidate reaches the interface; repeatability remains open (2026-10-13)
- Baseline dc708dc: camera candidate offline only, public motion/routing from
  simulator state. Added optional CameraTasks/CameraPerformance adapter through
  original task/MCP bus. Rack context from calibrated RGB-D; both language paths
  omit object coordinates; separate original physical evaluator owns success.
- Camera detection worker runs while native physics advances under shared
  gravity hold; epoch guards reject stale commands/results. Cancelled held
  generator cannot optimistically resume; preserve paused context for fresh
  destination plan. Missing next-rack context refuses before rerouting old task.
- -CameraTools starts separate8886/8885/8802; existing8876 remains untouched.
  Default scene6/6 direct pickup/return legs with actor truth access denied.
  Two complete interface sequences pass delivery, conversation, Stop/resume,
  verified old return before tool change and contextual return; final errors
  7.49/9.69/10.60/15.96mm, StopHTTP-to-observedstate53.25ms(earlier54.11ms).
- Reusable script's first actual run on already-returned poses failed during
  resumed screwdriver carry: grip changed, real drop, success withheld, later
  legs not run. Stop97.31ms, lift187.17mm. Confounds include changed starting
  poses and concurrent host load; cause unresolved, no threshold/fit change.
  Preserve failed state/frame/logs. Two successful sequences do not prove broad
  live qualification; earlier53/54 belongs to its frozen offline candidate.
- User reports "it worked." for main live microphone screwdriver journey.
  Main outcome9.65mm, applicationclock16.58s, no acoustic-latency/echo measurements.
  One human main journey confirmed, camera live voice/demo still outstanding.
- Final302 tests/lint/46protectedhashes pass. Local reports/raw traces retained;
  rollback omits switch. No mic activation, model fits, cloud upload or hardware.
  Next investigate resumed carry across returned poses, then full camera voice,
  latency, broader layouts and user-controlled demonstration. Goal remains active.
  Details/evidence: live-camera-interface-pc.md/live-camera-interface-pc-evidence.json.

## B29 — recovery wait and continuous pose carry repair (2026-10-13)
- Previous d975557 is concrete progress, with a retained continued-session
  resumed-carry failure. Frozen diagnostic baseline: ten legs succeeded, two
  failed, last return unreached. Both abort while observing after loss: owned
  one-attempt recovery has confirmed closed empty-gap, but computation wait
  demands a held handle. Fix only that phase, finite closed gaps [0,15mm) on both
  sides of each tick; carrying uncertainty persists until fresh supported camera.
- Corrected alternate-view detector to use cooperative physics. This exposed
  repeated hammer-return freshness failure: two views took440ms. Profile showed
  duplicate full-image depth/color preparation across fallback passes. Reuse
  within one frame; exact outputs on48 frozen optical cases and2 failed-frame
  captures, five paired trials each. Their medians154/247→67/118ms. No fitting,
  cross-frame cache, confidence changes or relaxed250ms freshness.
- Closed-empty-hand retreat/resurvey prototype still cannot fit the dropped
  wrench. Rolled back; rejected images/trace retained, no third similar fit.
- New hypothesis: continuous Cartesian transport/descent and smooth shortest
  wrist rotation preserve grip through intermediate motion better than joint
  interpolation. Optional cartesian_carry leaves old actor/default main off.
  Original.075rad/solver/refinement caps unchanged. Plans>200ms measured: separate
  kinematic worker/captured robot readings, real physics under gravity while
  waiting, epoch/stale250ms/measured-first-waypoint checks before movement.
- Final diagnostic13/13 physical legs; external truth observer at every physics
  tick independently confirms original lift, placement, rest, open-hand and
  unrelated-tool gates. Known/repeated replay, not unseen rate. Original losses
  retained; pose geometry/orientation/timing changed together, no speed-only claim.
- Three live interface sequences in one continued session, all12placements,
  conversation, Stop/resume, old-tool return before change, contextual return.
  StopHTTP→observedstate63.64/112.00/24.62ms, n3, no acoustic claim.
- Actual Windows saved speech natural semantic request → CUDA ASR → Bonsai model
  → original bus → camera delivery/return. ASR315.55ms, model507.49ms,
  native decision538.71ms; delivery7.52mm/lift201.95mm, return9.55mm. n1 warm,
  quiet benchmark window. Substantive acknowledgment cannot meet0.5s in this
  sample; full utterance/audible timing, distributions/contention still needed.
- Full315tests/lint/46protectedhashes pass. No ASR fallback, new models/fits,
  mic activation, raw-data publication or hardware. Main8876 remains ready,
  candidate8886 ready. Broad prospective actual-adapter layouts and recovery
  after cancellation inside computation remain outstanding; held resume currently
  refuses/retains context for fresh destination. Human camera demo pending.
  Goal active. Details/evidence: live-camera-recovery-pc.md/live-camera-recovery-pc-evidence.json.

### B30 — Existing robotics components and decision models (PC, 2026-10-13)

- Previous goal turn is progress: primary-source model research changed the
  strategy toward existing execution components and pretrained skills. User
  explicitly challenges excessive work on custom basic arm functions.
- Inspected immutable Strands Robots a6f2e776 and Decider b9fc8362 sources.
  No external issues, messages, paid calls, recordings or hardware. Main8876
  and camera8886 remain on their existing runtimes; no dependency changes there.
- Robots source removed its vendored LIBERO adapter; stale embodiment entries
  do not supply one. Preserve our verified OpenPi/LIBERO stack. Generic robot
  joint execution cannot consume LIBERO delta-EEF actions by matching lengths;
  remote WS-JSON is also not our OpenPi wire protocol.
- Separate real MuJoCo probe uses unchanged workbench Panda XML. First run fails
  because local-file action names are actuators, while observations name joints.
  Explicit XML-validated arm mapping and original split-tendon 0..255 open-hand
  units resolve it. No pretrained model, grasp, object attachment or tool claim.
- Final probe: 3/3 joint execution/cooperative cancellations, observed terminal
  latencies23.68/19.75/22.07ms, n3 warm. Physics advanced independently another
  1simsecond: every arm drifts0.03792rad, violating existing0.02rad hold bound.
  Workbench Stop is unqualified; original32s/tool hold test not run. Do not
  conflate ending policy execution with physical braking or audible Stop.
- Inspected before/after rendered PNGs; framework reports llvmpipe software
  rendering. No GPU rendering speed claim. Source package installed from
  immutable archive into separate Linux/tmp environment with evaluation-only
  version after two Windows-mount Git timeouts; an owned pip installer blocked
  on p9 filesystem RPC was stopped before moving the disposable runtime.
- Built-in primitives explicitly lack collision awareness. MoveIt2/cuRobo
  wrappers deprecated; evaluate maintained planners independently rather than
  adopt obsolete wrappers. Decider source inspected, checkpoint not yet run.
- Added reusable standalone runtime probe; its lint passes. Raw failed and
  successful runs remain local. Curated result: strands-selection-evidence.json.
  Earlier async-camera cancellation edits remain unpublished and incomplete;
  their best known diagnostic22/23 is not promotion evidence. Next priority:
  local Decider comparison and existing manipulation components behind our
  working voice/task interface, with original independent physical judges.
  Full assistant goal remains active.

### B31 — Actual local Decider versus Bonsai (PC, 2026-10-13)

- Previous goal turn is progress: 81fc8ce published a real Strands/Panda probe
  and a measured physical holding failure, changing the integration strategy.
- Freeze existing dialogue/context/quality fixtures before inference:31unique
  cases,3repeats; merged SHA aed016fa54905b47478d8181fadd701435dae51fa81a604933bf2ac7dedf4593.
  Question/options/0.9confidence threshold frozen in new protocol, no tuning
  after failures. Judges preserve existing permitted action/object expectations.
- Real read-only native Bonsai baseline93/93, median591.02ms,p95714.79ms;
  native job49fd23dd unchanged. No motion or microphone. Includes intent/reply
  generation and HTTP; candidate below only selects an action, direct engine.
- Decider code b9fc8362, public adapter216d1ccb, Qwen2Bbase b1485b2f pinned.
  Head/adapter match exported provenance SHA; base weights4,548,221,488bytes
  and tokenizer match published LFS SHA. Publisher says base training revision
  inferred, not pinned by training hosts; preserve that limitation.
- Initial Xet transfer stayed at6.6MB while live; ordinary exact-file HTTP200
  confirmed. Stop only owned inspected transfer; HF_HUB_DISABLE_XET=1 then
  completes6m40s. Same immutable model/cache, anonymous download, no upload.
- Separate Linux/tmp environment: Torch2.14.1+cu130,Transformers5.19.0,PEFT0.21.2.
  Actual bf16 CUDA matmul passes; compiledsm120 and all model parameters CUDA.
  This improves our prior Torch2.7.1cu126 GPU incompatibility evidence without
  modifying the OpenPi JAX lab or public ASR/controller environments.
- Offline actual checkpoint inference:60/93correct,33wrong (11unique failures).
  Warm92median45.40ms,p9558.78ms; load2391.69ms,firstrequest6694.24ms.
  Peakallocated4,080,733,696bytes. Reference PyTorch CUDA conv/gated-delta;
  causal-conv1d/FLA absent and explicitly reported, no CPU inference fallback.
- Errors include physical fetches for information/hypotheticals and unsupported
  repair/assembly; negated fetch selects return. Unsupported assembly fetch has
  confidence0.9217, repeated3times. A0.9confidence gate alone is insufficient.
  Do not promote this configuration. No claim all Decider uses/models fail.
- Vision briefly unloaded for measured candidate, Bonsai stays resident; vision
  restored automatically. Both runtimes idle/ready, no robot requests sent.
  Prefixcache disabled. Known fixtures/repeats, unequal reply/transport scopes
  and GPU inventories disclosed; no end-to-end or contention-target claim.
- Added immutable checkpoint preparation, frozen benchmark and Windows launcher
  with finally restoration. Python lint and launcher syntax pass; raw identity,
  rows/weights remain local. Curated: decider-task-selection-evidence.json.
  Keep Bonsai; shift next work to existing manipulation components and pretrained
  skills, preserving independent contact/lift/placement/Stop judges. Earlier
  async-camera patch remains unpromoted. Full goal active; live camera user
  feedback, prospective journeys and complete acoustic latency still outstanding.

### B32 — Maintained motion backend in complete journeys (PC, 2026-10-13)

- Previous goal turn is progress: actual Decider inference33/93errors retained,
  high-confidence unsupported-work fetch rejects promotion. Shift from further
  classifier tuning toward existing manipulation components, per user steering.
- Mink1.3.0/QP/DAQP adapter uses robot readings only, independent IK data and
  zero-velocity constraints on irrelevant DOFs. Real tools retain their original
  free-body/contact dynamics. Original residual/iteration/joint-continuity and
  Cartesian refinement caps remain. No fits, poses/velocities, welds, contact or
  force changes. Scene collision constraints not enabled in this first adapter.
- Freeze protocol before inference: seeds42/77, three tools, original/mink paired
  fetch32sStop/resume/return journeys. Use published296cc6f source archive to
  exclude unfinished async-camera patch. Planner cannot access bench.observe or
  tool_support_height. Independent evaluator samples every actual physics tick.
- Original12/12legs; Mink12/12legs. Mink6/6holds each32simseconds; maximum
  joint drift0.00025130rad,tool drift0.00033053m. Original35mm/80mm/rest/open/
  unrelated4mm and hold0.02rad/10mm judges unchanged. Known default layouts,
  no prospective rate or superior speed/reliability claim. Raw:mink-motion-001.
- Launch separate native8895/Dum-E8896/MCP8803 with pinned isolated numerical
  components and frozen original app/task/bus. ExplicitCPU/int8ASR preserves
  existing GPU services. No microphone activation; main8876/camera8886 preserved.
- Actual typed interface sequence passes conversation,Stop/resume,tool change
  with prior return,and contextual return. Four successful independent placements;
  all four tasks confirm actualMink solves170/132/132/131. HTTPStop23.28ms n1,
  no acoustic or physical settling latency claim. Raw:mink-live-6e93d0bc.
- Initial live launcher edited while running, causing a shutdown parsing error
  after owned cleanup. Processes confirmed terminal. Fix executes frozen shell
  copy per session; freshmink-live-897cf930Ready,CPUASRready,renderedJPEG inspected.
  Frozen-copy cleanup exits0, owned process IDs terminal. Immediate restart probe
  initially rejects TCP TIME_WAIT despite no listeners; use original app's
  SO_REUSEADDR setting. Finalmink-live-28944f90Ready. Occupied live ports refused
  before starting services. Do not edit live launcher copies.
- Reusable standalone adapter/comparison and PC launcher added. Python lint,
  shell syntax and PowerShell syntax checked. Full public-controller suite not
  rerun: no production imports/defaults changed; unfinished source patch remains
  unpromoted. Some camera releases remain unverified by actor; original independent
  simulation judge confirms placement. Details:mink-motion-pc.md/evidenceJSON.
- Next: prospective varied-layout journeys for maintained backend, planning-time
  cancellation and measured full speech/acknowledgment. Main policy lab3/3native
  success and2/3strictqualification remains separate; no trained-policy replacement
  or hardware readiness claim. Full goal active, live human feedback outstanding.

### B33 — Prospective maintained-backend camera journeys (PC, 2026-10-13)

- Previous turn is progress:6a3ae58 publishes the maintained IK adapter,12/12
  known-layout physical legs,six32s holds,and a real four-placement bus sequence.
- Freeze actor/reference296cc6f,all robot assets,maintained adapter,judge,recipe,
  dependencies before generating54newcases; seed2026101305. Original lane/yaw/
  light distribution and protected criterion fixture unchanged. No filtering,
  sample replacement,fits or threshold changes. Manifest0d7c4b11;fixture21e9b91c.
- Extend reusable verifier to actualCameraTasks deliver/resume/redirect journeys
  and contextual return. Actor object-state/support-height access refused;
  independent truth judge samples every actualphysics tick. Preserve35mm/80mm,
  rest/open,4mm unrelated-motion gates plus existing stricterhold checks.19frame
  short hold here; separate32s qualification retained. Old unfinished async
  camera edits excluded from experiment via frozen reference archive.
- All54journeys per backend,90legs each,180actual leg rows. Both52/54complete
  journeys (96.296%),88/90legs,pass original95%observed criterion. Post-run
  actor/judge/recipe/runtime manifest identical. No overall improvement claim.
  Wilson95 interval87.46–98.98%,not95%population guarantee.
- Raw report inherits default-layout scope text; fixture/source identities and
  all54cases establish prospective scope. Metadata-only label corrected after
  the unchanged-manifest check; no controller,judge,cases or results changed.
- Original fails005hammer return on4.457mm unrelated movement (4mm cap),049wrench
  return onstale frame. Mink fails021screwdriver return onambiguous neighboring
  wrench,027screwdriver return onstale frame. BothMink refusals leave the held
  tool around219mm high; do not claim release/completion. Failures retained.
- Per-tool journeys: original screwdriver18/18,wrench17/18,hammer17/18;
  Mink16/18,18/18,18/18. This is a whole-adapter test,notonlybarecontrollerIK.
- Unpaced leg execution med/p95: original1535.06/2313.20ms,Mink1530.14/2140.76ms,
  n90each; excludes hub setup,language,speech,andacousticoutput. No live-speed
  target or contention qualification inferred. Raw:mink-cohort-001.
- Curatedmink-cohort-evidence.json,source freeze/generation helper and recipe
  added. Actual current main/camera/Mink demos preserved; no real hardware,
  microphone activation,external messages or data uploads. Candidate remains
  experimental pendingplanning-timecancel/resume and fullspokenmeasurement.
  Sourceasyncpatch remains incomplete. Full assistant goal active.

### B34 — Human voice failure and continuation/cancellation repair (PC, 2026-10-13)

- Human reports late Stop and a second screwdriver pickup on Proceed. Matching
  live logs are main8876/dume-2f3fadf5, not the earlier camera8886 automation.
  Stop clip7.44s, ASR261ms, native interruption about72ms after request;
  final-word timing missing. Do not infer endpoint delay from clip duration or
  claim a passing live demonstration. Proceed was model-classified as fetch.
- Current-state continuation bypasses model classification and pending dialogue
  clarification; completed/working/idle states do not launch a pickup. Native
  continuation also overrides an incorrectly supplied resolved fetch. Baseline
  post-release resume completes withdrawal and the original judge without
  reacquiring the tool. Original lift history and placement limits preserved.
- Camera async repair waits for abandoned pure workers before new snapshot
  timestamps, discards old result/errors, and validates phase/grasp state before
  replacing generators. Original recovery/correction budgets preserved. Legacy
  real-worker cancellation23/23 with32s holds; Mink quiet21/21 nominal, two
  known loss phases never entered (actual success, recovery attempts0). Whole
  Mink protocol21/23 remains incomplete; earlier20/23 stale refusal retained.
- Add capture/detector diagnostics and server transcript timestamps without
  recording audio, automatic mic access, or altering speech thresholds. Explicit
  alternative launcher ports preserve existing demonstrations. See
  voice-state-repair-pc.md. Spoken Stop responsiveness and full goal remain open.
- New separate camera instance8986/dume-f6e36b53 is live, explicit CPU/int8 ASR,
  recording off by default; original three services preserved. Typed actual bus
  Stop-during-carry/Proceed/delivery/completed-Proceed/no-new-task/contextReturn
  passes1/1. Observedlift212.84mm, rackerror6.84mm. Rawcontinuation-live-001 and
  renderedframe retained. This does not establish speech latency.
- Full suite329passed204.04s,24dependency/multiprocessingwarnings; bothJSvoice
  contracts pass; Ruff clean and46upstream bytes verified unchanged. Source
  repairs now reviewable; full live acoustic demonstration still outstanding.

### B35 — Reproduce noisy late Stop misses; prospective speech-edge candidate (PC)

- Previous turn is verified progress: de9bfde publishes current-state continuation,
  post-release resume and camera-worker cancellation; live typed journey passed.
- Human Chrome session was8876, not8886. Mac endpoint raw clips absent on PC;
  generate a separately identified PC corpus from available SAPI fixtures.
  Protocolf033e027:27cases; mock-ASR real browser stream27/27, queue peak1,
  Stopcallback472.05/545.50ms med/p95 n12. Actual CUDA ASR24/27: three noisy
  Stops after5s background rejected. Successful9Stopcallbacks767.20/827.80ms;
  failures not omitted from reliability. Energy baseline18failures,2noise submits.
- Installed maintained Silero outer-edge trim preserves all interior samples,
  existing0.3/120/350browserparameters,default400ms padding,originalWhisper
  confidence gates/checkpoint. No fitting/search. Relay known27/27 but extra
  decode/cold latency:1017.90/2945.30ms Stopcallbacks n12; retained.
- Add experimental SpeechInput(edge_trim=True), defaultFalse. Native prewarming
  actual VAD+CUDA avoids relay double decode. Fresh source/protocol/code/PCM
  identities frozen before reserved inference; protocol98026583,26cases,
  onsets2/7s,gains0.7/0.13,noise newseed,negations/Stopdiscussion included.
  Actual browser/nativeCUDA26/26,negativeStopcallbacks0,noise submits0;
  eightStopcallbacks779.55/907.80ms med/p95,max907.80. Preproc3.5/10/12ms
  med/p95/max n24. Independent frozen-code/PCM/meaning/timing judge passed.
- Native preparation3.935s,warmup2.007s; Whisperimmutable d1d751a5,FP16CUDA,
  ONNXCPU VADv6 hash4cbf549b; ORT1.31.0,faster-whisper1.2.1,CTranslate2 4.8.2.
  Loader/source-generation failures preserved, no device fallback or invalid
  empty-file samples counted. Detailed scopes inpc-speech-edge-preprocessing.md.
- Candidate is not enabled in the running assistants. Measurements end at
  browser Stop callback, notnative cancellation/settling or human final-word
  acoustics. Next gate: actual moving-arm interruption using this speech path,
  pending-model cancellation, continuation, fullspeechack and human validation.
  No mic activation/realhardware/external messaging/rawdata upload. Goal active.

### B36 — Full natural voice interruption with explicit CPU Stop isolation (PC)

- Previous turn is progress:684c9b6 publishes edge preprocessing, retained24/27
  miss baseline and prospective26/26 CUDA callbacks; physical timing not claimed.
- First physical run has12native placements but browser report exceeds100KB;
  visibleStopPOST4/6above1s, rawDOM/frame/native events retained. RevisedGPU-only
  fullvoice run005 verifies6pendingcamera interruptions but only5fulljourneys;
  connectionfailure interrupts last resume. Conservativeupper Stop1144.05/1244.10
  ms med/p95,5/6above1s. Browser/WSL clocks diverge; matchnativeJobIDs and bound
  cancellation between POST/ack inbrowserclock. Same1000ms criterion, separatehold.
- InstalledPyAV19.0.1 nativeboundeddecoder preservesoriginalgates. SavedWAV
  warm24 med/p95 drops184.10/208.85 to5.83/11.64ms, maxsampledifference<1e-5;
  firstimport272.70ms happens before readiness. Realmono/stereo and badinput
  tests pass. OldFFmpeg7 misdetects periodic48kstereo asMP3; declaredPCMreference
  retains numericagreementgate. Actorphysics/uncertainty limits unchanged.
- Explicit opt-in CPU tiny.en positiveStop path, general speech stillCUDA small.en.
  Officialimmutable0d3d19a3,78,091,917bytes publisherhash verified. ActualCPU INT8
  53retained semanticcases correct,0falseStops;20positive med/p95171.15/199.03ms
  withoutbrowser/motion. No training,hotword orconfidence relaxation. NonStop/
  negation keepsprimarymodel; missingaux readiness cannot silentlyswitchdevices.
- Fullregression exposesforkchildsegfault and1cameraHammer failure withoutreason;
  do not infercamera cause. Explicitspawn manager startup added inruntime/tests.
  Focused28pass; full343pass256.07s,1dependencywarning,no fork warnings.
- FinalCPU run007 completes6/6 fullvoice journeys: naturalfetch,actualcamera
  question,Stop,Proceed,completedProceed/no repick,return. Allphysical/state
  checks pass;4native-verifiedpendingmodel replies superseded.12placements,
  minlift201.53mm,maxerror9.56mm,maxjointdrift0.000940rad,heldtranslation0.865mm.
  Capturetracks ended; source/PCM posthash checks pass. Original35mm/80mm/4mm,
  0.02rad/600ms/elevated/retainedgrip/noqueue/pendingcriteria intact.
- Conservative Stopupperbounds931.90/1012.40ms med/p95 n6;5/6within1000ms.
  Sixthactualnative onset bounded925.60–1012.40ms:deadlineunproven. Overalltiming
  gate fails; notpromoted. Need precisecancellation versusqueueack measurement,
  fullacoustic/ack/echo/humanvalidation andbroadercontention. Experimental8996
  ready, originals preserved, no mic activation/hardware/rawupload. Goal active.

### B37 — Verified camera workload and conservative cancellation intervals (PC)

- Previous turn progressed state/physical voice checks and CPUStop isolation,
  but run007 did not prove the intended Gemma workload: subsequent log inspection
  found2timeouts and4different-model identity refusals. Physical/state results
  remain valid; withdraw intended-camera-contention qualification. No hiding errors.
- NativeStop still precedes task cleanup. Add logged monotonic start/ack/cleanup
  intervals and uniqueID; endpoint returns identical record. Judge verifies local
  record/duration/order and subtracts only post-ack cleanup,roundeddown wholems.
  Same1000ms target, no browser/WSL wall-clock subtraction; holdcriteria unchanged.
- Full344tests pass229.31s,1dependencywarning; new ordering/logging contract passes.
  Run008fails after2journeys because camera identityfailure becomes409 beforeStop
  supersedes it. ActualStop transcript/nativecancellation present; failedrun retained.
- Loadedinventory had onlyBonsai; selectedGemma absent,causeunknown. Explicitlyreload
  localGemma4 31B Q4_K_M,maxoffload,4096context,1slot,3600sTTL; realcameraresponse
  verifiesexactalias. Preserve observedBonsai8192context/4slots. No model fallback.
- Freeze same6sources/PCM/code/protectedcriteria again,protocolb3bd58dd. Judge now
  rejectsfailedcamera workloads eveniflatersuperseded; stricterevidence, no actorchange.
  Retry009passes6/6 fulljourneys +6validpendingcamera interruptions,12placements;
  no completedProceed repick. Minlift201.33mm,maxerror9.24mm,maxjointdrift0.001438rad,
  heldtranslation0.520mm,maxobserverage135ms. Posthash/criteria checks pass.
- Stopupper861.00/979.70ms med/samplep95 n6,all<=1000. Cleanupfloor0/0/2/1/1/1ms;
  uncorrected861.50/980.70also pass. No causal speedup claim from this rerun.
  Seven retainedrecord mutationchecks,Ruff,browsercontracts,46upstream bytes pass.
- Experimental8996Ready, originaldemospreserved. Next: human-controlled fastStop/
  stateawareProceed demonstration, acoustic/ack/echo measurement, broadcontention.
  No micactivation, hardware, rawupload or externalmessages. Sustainedgoal active.

### B38 — Neutral acknowledgment before interpretation; real playback lifecycle (PC)

- Previous13793e7 turn verifies6complete savedvoice journeys under intendedGemma,
  Stopupper861/980ms med/p95. Livehumanfeedback remains pending; goalnotcomplete.
- SerialASR+decision in6retained naturalfetch cases has589/1095ms lowerbounds,
  excludingtransport,polling/playback. Addneutral idle-request cue aftercapture
  closes,neverawaited byASR/Stop. Movinginterrupt recordings remain silent.
- Browser-synthesis trials001/002fail;002showsenqueue/end11ms,no start despite
  ASRsuccess. Directactive-click/retainedutterance/English diagnostic ends10ms
  withoutstart too. Preservebothfailures; no browser/OSrootcause asserted.
- Changeplaybackstrategy: precompute fixedWindowsSAPI WAV, playwithHTMLAudio;
  ordinaryreplypath retained. Launcherpreparesmissingcue,failedpreparationdoes
  notblocktypedassistant. Backendcapability gatescue, preservingolderdemos.
  Echoexactphraseguard requiresactualstart,expires3s, survivesnewerreply;
  Stop/toolcommands independent. Playbackgenerationsrejectlate/staleevents.
- Frozen8cache trials003pass37.75/56.60ms med/p95 completion-to-playerstart.
  Actualmidplay cancellation pauses at.172s;64usadvanceover250ms. CuePCM first
  voicedframeends120ms (20ms,RMS.008), waveform1.644s; no acousticonsetclaim.
- Fastreplycouldtruncatecue: outputonlywaituntilcueend,latestreplywins;Stop/
  mute/newutterance cancelsqueue,2sboundedwait. Final8overlap trials004pass
  33.80/49.30ms playerstart;153.80/169.30ms includingvoicedframereference;
  wholecue1682–1720ms. Wordend-to-player1063.10/1123.50ms includessame900mspause.
  Source/code/asset andregisteredgeneration checks pass, no robotcommands sent.
- Six alteredrecord checks pass inWSL; missingcase,expandedtarget,unregistered
  start,truncatedcue,latecue rejected. WindowsTmp permissions preventedthatcheck,
  no originaldata orpermissionchanges; useprivateWSLtemporary storage instead.
- Full346tests pass219.03s,1warning; finalAPIcapability15pass4.86s; JScontracts,
  Ruff,PowerShellparsers,46upstreamfiles pass. Updated8996Ready,primaryactualCUDA,
  explicitCPUStop, exactpreparedWAVserved;3.619spreparation/2.368swarmup beforemic.
- Remaining: roomacoustic/ordinaryreply/echo checks, movingconversationack,
  fullcue-enabled physicaljourney andbroadutterances. Originalsremainrunning;
  no micactivation/hardware/rawuploads/externalmessages. Goalactive.

### B39 — Real installed Windows reply output with cancellation-safe IPC (PC)

- Previous5330039 qualifiesneutralcue softwareplayback; ordinarybrowser synthesis
  failed tostart and humanacoustic/echo checks remain pending. Goalnotcomplete.
- Verify persistentPS5/System.Speech worker fromWSL:12validWAVs,814.48mscold,
  18.2–64.9ms roundtrips. InstalledMicrosoftDavidDesktop,stdinJSON only,no speakers.
- Explicit-WindowsSpeech opt-in integrates actualworker throughasyncAPI/thread,
  bounded500chars/10s/2MB/45s/3MBresponse. WarmbeforeoutputReady; configuredfailure
  returns503,no browserfallback. PhysicalStopneverwaitsworkerlock; nativeaudio
  gen/currentURI protectsstaleoutput. Duration-awareecho,acceptedstart/end logs.
  Onlyneutralcuequeuesreply;ordinaryaudio canbesuperseded. TypedStoppausesaudio.
- RealAPI/browser001 completes12/12,66.85/100.80ms med/p95textready-to-player.
  Final002 completes12/12 withacceptedstart/end,67.00/100.60ms; lateNativegen13
  discarded,no audioURI/WAV/browserstart. Source/WAV/wholeplayback checks pass.
  Six altered-recordchecks rejectmissing/wrongvoice/incomplete/late/staleadvertising.
- IndependentCUDAreadback10/12exact; bothothercasesstoppedtask→stoptask,12accepted.
  Retainmismatches, no tuning/gaterelaxation orperfectspeechclaim. No acousticproof.
- Full349tests pass225.29s,1dependencywarning; nativeAPI blocked-synthesis Stop,
  lateoutput,expiredURI,nofallback regressions pass. ExistingJScontracts pass.
- Reviewmoves activearm cancellation before potentiallyslow speechworkerclose;
  orderingregression added,final350pass214.74s/1warning. All12actualreadbacks
  rejected bysoftwareecho;Stop/return/newtoolpreserved, no microphone/roomclaim.
- Updateidle8996,rundume-d20e0c18,actualnativeoutputReady/CUDAsmall/CPUStop/cue.
  ASR4.468spreparation/2.416swarmup. Profilegenerates/servesnativeWAV. Gemmaabsent
  fromloadedinventory: restorelistedlocalmodelkey,verifyQ4_K_M+alias+nullremoteID;
  variantmetadatakeynotacceptedCLI, failedattemptretained. Originaldemospreserved.
- Final350-tested deploymentdume-4db6ecb8 Ready; input3.547spreparation/2.312swarmup,
  actualnativeWAVserved. Allspeechprobes/oldworkers gracefullyclosed; oneowned
  worker remains with the liveexperimentalprofile. Originalfourservicespreserved.
- Remaining:fullspeech-enabledarmjourneys, humanaudibility/acoustic/roomEcho,
  movingconversationack andbroaderassistantgoals. No micactivation,hardware,
  paidservices,rawupload or externalmessages. Sustainedgoalactive.

### B40 — Full saved-voice speech/physics journeys in isolated profile (PC)

- Previousb8cb452 adds actualWindowsordinaryreplies,350regressions pass; full
  speech-enabledarmjourney andhumanroom checks remain open. Progressnotcompletion.
- With935MBfreeGPU, temporarilycloseidle8996 andlaunchsameCUDA/CPUStop/native
  speech camera profile on9036/9035/8806. Neveropen itspublicmicpage; generated
  streams only. Fouroriginaldemos preserved. Actualrenderedarm view inprobe.
- Preserveoriginalsixcases/criteria. Supplementnativeoutput lifecycle checks;
  fullStop/delivery/completedProceed/return replies finish,4ack percase required.
  NoAPI/actor tweaks. Run001preparedunused afterlabelrepair;002failsafter1row
  onobserverunfinishedreply despite nativeendedlogs. Retainfailedqualification.
- Testobservermonotonicmessagecount matchespublicUI; oldpollcannotreplayreply.
  MarklogicalqueuedreplysupersededbeforeAPI dispatch; persistfailure/media clocks.
  Bothracecontracts pass. Addedmediaendpointcheck,keptoriginalduration tolerance.
- Final003passes6/6 physics/state/speech/timing;12placements,minlift201.30mm,
  maxerror9.26mm,drift0.002471rad,heldmotion0.392mm,5nativependingcamera interruptions.
  ConservativeStop802.25/965.60ms med/p95 n6,all<1000; no target orclockchange.
- All24acks/42ordinaryreplies complete;ackstart64.10/124.10ms n24,API-to-player
  95.45/151.80ms n66,outputqueuewait separate. Fourackedidlecommandspercase;
  completedProceed no repick,return contextcorrect. Source/PCM/WAV/nativeevents pass.
- Sixnegativeevidencechecks rejectmissing/truncated/late/failedoutput; observer,
  recorder,output,static and46upstreamchecks pass. Priorproduction350pass retained;
  thisturn onlytesttooling. No extrapolation tolive acoustic/audible performance.
- Restore8996Ready,d9410c6e,CUDAsmall/CPUStop/SAPI;ASR3.268spreparation/2.146swarmup.
  Isolatedtestservicesgracefullyclosed. Humanmic/echo, broadutterances/layouts,
  learnedpolicy andwholegoal remainopen. No microphoneactivation,hardware,
  paidservices,rawuploads or externalmessages. Sustainedgoalactive.

### C — Exact replay diagnoses the failed pretrained-policy grasp (PC)

- Previous model-review turn provided verified advice but no implementation
  change; resume the policy milestone rather than repeat a status summary.
- New evaluator-only diagnostic replays task0/epoch1 from execution-boundary-010,
  corresponding to failed live-voice-012. All103 actions, including inference
  waits, are retained. No new inference, GPU-model change, microphone or hardware.
- Original OSC, seed7/state0/ten initialization steps; all103 endpoint object and
  joint positions, simulated times, grasp and success checks match exactly.
- Observe2,678 native torque-callback/endpoint samples with unchanged torques.
  All393 samples above80mm contact left pad and both finger bodies; right pad
  never contacts. Maximum lift119.446mm, bilateral-pad maximum9.526mm.
  Polling aliasing cannot explain the missing qualified grasp in this replay.
- Native placement succeeds. Contact geometry alone does not establish unstable
  grasp; retain original2/3 qualification and protected pad-contact/80mm gates.
- Raw contact-diagnosis-001 preserves samples, comparisons, protocol, image and
  frozen actor. Documentation records source/actor hashes and reproduction.
  Next: separate frozen grasp-adaptation/recovery experiment, with this known
  trace confined to diagnosis/development and independent held-out evaluation.

### C — Frozen 3 mm alignment experiment changes physical grasp outcome (PC)

- Previous b373dc9 is verified progress: exact replay diagnoses right-finger body
  contact instead of the required pad. Hypothesis: small approach alignment
  changes can establish bilateral-pad contact without changing geometry/judges.
- Freeze baseline and six +/-3mm world-axis variants before physics execution;
  one attempt grid, no retuning. Apply once at last open-gripper action56.
  Native OSC scaling0.05m/input verified, correction0.06input; all other recorded
  actions retained. Evaluator truth only triggers/measures pause, not correction.
- Unchanged103-step baseline reproduces source physics exactly. X-/X+/Z-/Z+
  reach80mm bilateral pads, retain them during nativejointkp300/damping2 hold,
  and place successfully after resuming recorded actions. Y- fails grasp trigger
  and native placement; Y+ places but never reaches qualified grasp trigger.
- Four held windows advance1.05sim seconds over3.215–3.437wall seconds;
  minlift80.087–85.807mm, motion2.550–5.508mm, joint range0.007963–0.017203rad.
  All original LIBERO physical gates retained; no ASR/Stop latency claim.
- Raw grasp-alignment-001 includes all7 outcomes, exact action/hold traces,
  frozen actor/protocol and videos. Independent raw audit checks action edits,
  all baseline states, metrics, denominator and hashes; rendered hold inspected.
- This is one known-source counterfactual grid, not seven independent learned
  policy rollouts or held-out cases. Original2/3 qualification unchanged; no
  adapter enabled. Next: separately frozen paired fresh-policy experiment with
  explicit RNG and refreshed observations after interruption, no repeat grid.

### C — Fresh policy comparison rejects universal offset and exposes brake failures (PC)

- Previous3a0b7e8 is progress: frozen replay4/6 corrections improve physical grasp;
  move to actual closed-loop checkpoint feedback rather than another replay grid.
- Add explicit opt-in seed/draw policy endpoint; pinned nativeJAX fold/split,
  no upstream edits or default-server RNG/interface changes. Actual repeated
  same observation/seed/draw actions exactly equal. Initial helper import-path
  mistake corrected before cohort; no policy episode dropped for that setup error.
- Freeze all3 layouts×2 policy seeds101/202×baseline/candidate=12episodes.
  Candidate+3mmX occurs first closing command, one action later than replay.
  Continuous physics and wall-time waits prevent exact pre-intervention pairing;
  no isolated causal-effect claim. NPZ archive hash is not semantic array equality.
- All12 native placements succeed. Combined gate: baseline4/6, corrected1/6.
  Two episodes lack qualified grasp; four exceedjoint20mrad, another loses pad
  contact and moves13.494mm>10mm. Ten triggered episodes discard old work,
  reject stale generations, hold physically and request fresh inference onresume.
- Original pad/contact/lift/hold/active budgets retained; terminal positive grip
  does not establish release/resting. No voice/hardware or broadheldout claim;
  original2/3 voice qualification unchanged. Reject candidate, no adapterenabled.
- Actual268 warmed requests median/p95/max130.79/217.99/353.49ms afterpreprocessing;
  GPUload26.021s,warm15.885s. TemporarilyunloadGemma; Bonsai/ASR stayresident.
  Closeownedpolicy484775/sim485001, verify8900/8901closed; Gemma restoredlocal
  Q4_K_M/4096/1slot/3600s. Existing8896/8996 PIDs preserved.
- Independent raw audit checks12denominator, singleactioncorrection, holdmetrics,
  native physics goals and freshpost-resume calls; raw actors/hashes retained.
  Ruff/46upstreamchecks pass. No public controller edits. Next: bounded native
  braking experiment using failed velocity/hold windows, then prospective cohort.

### C — Dense native braking replay and torque saturation (PC, 2026-10-14)

- Previous44d5eb7 is progress: real12-episode policy comparison rejects offset.
  Freeze kp300/d2 baseline, kp300/d4 and kp600/d2 on all10 lifted stop windows.
- Match source reset via active_step1/running; match brake diagnostics to exact
  Stop request because old diagnostics can persist and state tags race scene
  reset. Clear old diagnostics on actual initialization; no physics change.
- Retain two setup failures: initial reference after controller construction,
  then timestamp dictionary overwrote one MuJoCo cache phase. Third run preserves
  both phases for reference matching and all samples for physical scores.
- All30 pre-brake trajectories/entry targets match exactly; baseline held samples
  within1e-6. Dense callback/endpoint checks: baseline4/10, each higher-gain5/10.
  No profiles enabled, no threshold changes. Two source no-trigger failures remain
  in original12 denominator. Known replay is not fresh/voice/held-out qualification.
- Dense sampling exposes20.309mrad excursion where source polling saw19.978;
  original4/6 baseline is historical captured-snapshot result, not continuoushold.
- Worstjoint6 reaches31.410mrad; higher gains still>30mrad. Separate baseline
  torqueaudit002 confirms57.333N·m request versus12N·m cap,39/504 clipped callbacks.
  Audit001 recorder-name collision retained; no failed run supplies passing data.
- Raw braking-replay-003 and braking-saturation-002 keep samples, actors, profiles,
  matches and rendered images. Independent audit verifiesall30, bounds, snapshot
  matches and clipping. Standard plot inspected. Next: constrained torque allocation
  within original actuator limits, then prospective fresh-policy qualification.

### C — Native torque allocation improves replay but remains unqualified (PC)

- Publish dense braking audit be2108a, then change strategy from higher gains
  to constrained allocation of native PD acceleration error. Freeze baseline
  and allocator kp300/d2 onall10 known stops; no profile or weight retuning.
- Native M inverse least squares, BVLS1e-9/50iter, SciPy1.10.1 already installed;
  import/startup check before callbacks. Original torque caps and robot clipping
  remain. In-bound native commands unchanged; solver failure has no fallback.
- Twenty actual replays complete; baseline reproduces dense prior exactly;
  pre-brake and entry states exact. Known physical gate improves4/10 to6/10.
  Retain grip/motion failure, two joint-range failures and two lift-minimum
  failures (overlapping one case). Worst range31.410→25.141mrad stillfails.
- All5144 extra-callback costs median/p95/max0.008/0.021/10.732ms;227 optimized
  callbacks0.130/0.397/10.732ms. Maximum violates2ms real-time suitability; no
  hardware or whole-callback timing claim. Livewall/voice criteria not measured.
- Independent raw audit checks20denominator, original dense baseline metrics,
  all physical gates and every candidate torque bound. Raw torque-allocation-001
  preserves actors, samples, command/allocation vectors, timings andrenders.
- No running controller changed; original2/3 voicequalification unchanged.
  Next: different hypothesis, constrain carrying speed before Stop under torque
  and grasp/EEF requirements; preserve220budget and prospective full episodes.

### C — Carrying limiter rejected; scene-reset cache guarded (PC, 2026-10-14)

- Freeze robot-only OSC scalar limiter at10mrad modeled budget/50% torque reserve;
  original80/12Nm caps, joint hold, grasp/lift/motion gates and220 active steps stay.
- Known replay20 trials: baseline4/10, limiter0/10. Contacts retained and wrist
  range reduced, but all candidates fall below80mm at the original Stop time.
  Offline200ms onset uses future Stop time; not deployable qualification.
- Fresh attempt001 retains7/12 attempted,5 not run; wrong-scene hold timeline
  exposes old-step cache publication. Treat entire cohort as contaminated.
- Guard scene generation independently of command generation, callback and
  post-step/encoded-cache publication. Archived/current controlled race regression
  reproduces leak only before repair. Natural before/after reset probes see zero
  stale Ready samples (847/836); do not claim natural reproduction.
- Repaired same-parameter fresh002 completes12 episodes, actualGPU checkpoint.
  Baseline3/6 holds,5/6 native goals,2/6 combined; candidate4/6 holds,0/6 goals,
  0/6 combined. All6 candidates exhaust original220 budget. Reject limiter.
- 375 warmed calls111.68/127.68/295.81ms median/p95/max.918 limiter decisions:
  median scalar.0975, added computation.152/.261/.544ms. Not whole-loop timing.
- Independent raw audits pass20 replay/12 fresh, dense2ms coverage and hashes;
  11 coordinator regressions, Ruff and46 protected upstream bytes pass.
- Owned8900/8901 services closed; public8996 stillReady. Restore localGemma
  Q4_K_M/4096/1slot/noTTL; Bonsai unchanged. Fresh read-onlycamera1.362s correct
  three tools, epoch0, no microphone. Full audit/evidence: carry-governor-audit.md.
- Next: measured-velocity, grasp-sensitive control hypothesis; no retuning this
  cohort, no lowered gates, no promotion or new publicvoice claim.

### C — Measured-velocity short Stop brake rejected (PC, 2026-10-14)

- Change strategy from pre-Stop command limiting to first50ms measured-velocity
  braking; preserve all policy/grasp/prefix motion and captured joint goals.
- Torque b-rMv, largest common feasible rate capped1/dt, original80/12Nm bounds;
  25 native2ms callbacks, then originalkp300/d2 PD. No actor objecttruth input.
- All20 known-window trials complete; baseline4/10, candidate4/10, same failures.
  All maintain80mm lift; worstjoint range31.410→38.507mrad, grasp-loss unresolved.
  Reject, no runtime/publiccontroller enabling and no retuning/freshcohort.
- Independent audit recomputes20 physical gates, baseline within1e-6 and250
  feasible torques. Initial rate bitwise comparison corrected to1e-12 arithmetic
  tolerance across NumPyversions; no data or physicalthreshold changes.
- Addedcompute.048/.103/.702ms median/p95/max.240 transitions localmodel maxjoint
  next-velocity errors.000319/.001012/.001454rad/s. Prediction matches short
  transitions, but shared braking rate and omitted position control are poor.
- Next: independent dissipative joint braking/position correction or grasp
  adaptation; no further common-rate/window sweep. Fullaudit velocity-brake-audit.md.

### C — Alternative pretrained grasp policy preparation (PC, in progress)

- Change strategy after rejected braking experiments: evaluate official OpenVLA-OFT
  spatial checkpoint in the same supported LIBERO simulator before grasp adaptation.
- Pin source e4287e9 and custom Transformers bc339d9; checkpoint revision
  6d0231af0e48c5985f1ff86908f4674b84bc049b, public/ungated, MIT metadata.
  Downloaded files checked against publisher LFS SHA256 or Git blob identity.
  Whole checkpoint remains unverified while three large shards are downloading.
- Existing Torch2.7.1cu126 detects5090 but lacks sm120 kernels. Create separate
  Python3.10.20/openvla-oft-cu128 environment; preserve assistant/pi0.5 environments.
  Official CUDA12.8 Torch/vision install still live; no new GPU kernel claim yet.
- NVIDIA-hosted dependency transfers timed out; use same versions from official
  PyPI while Torch comes from cu128 index. Custom fork wheel built from pinned
  shallow clone; abort redundant full-history fetch.87-package inference lock
  resolves, but remaining dependencies are not installed yet.
- First checkpoint downloader intentionally replaced with bounded curl requests;
  it had made progress before stopping. Preserve/reuse partials and archived helper.
  Full-file identity must pass before model loading; no raw/model upload.
- Adapter matches publisher action conversion on128 chunks, preserves six OSC
  inputs, rejects3 malformed outputs. Not joint-target mapping or model execution.
- Prepare real BF16 kernel/checkpoint probes and inference-only bootstrap using
  original modules and identical enum, skipping unrelated training exports.
  These probes have not executed; no policy/controller promoted or motion triggered.
- Exact live sessions/provenance/next commands in local runs/openvla-oft/continuation.json.
  Keep existing downloads/install jobs; poll same handles. Public8996 and both local
  models preserved. Run kernels, install locked dependencies, then full checkpoint
  inference before physical comparison. Gemma stays loaded until that load needs GPU.

- Current continuation: original curl transfer completed shards2/3 but exited1
  on shard1 curl timeout28. It is terminal; preserve its first1.208GB prefix.
  Repair shard1 separately under checkpoint-repair-001, live session44517; do not
  overwrite root files until original transfer terminal (now confirmed).
  CUDA installer78021 remains live and writing library files; not a stopped job.
- Freeze six-case prospective protocol in openvla-prospective-protocol.json before
  model outcomes: three known layouts×two deterministic repetitions, original220
  budget including inference waits, eight-action publisher chunk and fullhold gates.
- Add independent --dense-hold-capture flag, leaving rejected motion profiles off.
  Real native smoke records524 samples at2ms intervals over1.046sim seconds;
  experimental profile initialize is rejected409. This is infrastructure evidence,
  not a lifted-object or pretrained-policy pass. Owned smoke simulator exits0;
  scene-generation regression and11 coordinator checks pass. Public8996 stillReady.

### C — Alternative pretrained GPU execution qualified (PC, 2026-10-14)

- Repair completes, publisher SHA matches; full21-file/15,454,694,095B checkpoint
  reverified. CUDA installation exits0; separate87-package inference setup passes
  dependency consistency. Existing assistant/pi0.5 environments unchanged.
- Real BF16 matmul/conv/layernorm/noncausal attention pass on cuda0, sm120 compiled.
  Not just GPU visibility. New Torch2.7.1+cu128/vision0.22.1, TFCPU2.15.1/NumPy1.26.
- Inference-only bootstrap initially hits another training-data initializer;
  exclude VLA package exports while retaining original model/preprocessing/mask
  code and identical normalization enum. Actual tokenizer/two224px images/8D
  proprioception and model-class imports then pass.
- Real checkpoint inference6 calls produces finite8×7 nativeOSC chunks onGPU BF16.
  Five warmed repeats99.55/108.51ms median/samplep95, identical outputs; load68.014s,
  discarded first warmup14.197s. One savedknownobservation; no physical/voice claim.
- Raw output/hash/actor audit passes. Restore localGemma Q4_K_M/4096/1slot/noTTL;
  Bonsai unchanged. Fresh read-onlycamera identifies3 tools; no microphone/motion.
- Publish reproducible sources/dependency pins/helpers and aggregate evidence;
  rawweights/observations/wheels staylocal. Next frozen6-case physical cohort,
  no prospective controller promotion. Audit: openvla-gpu-qualification.md.

### C — Real OpenVLA closed-loop Stop/resume cohort:5/6 combined (PC)

- Freeze3 known layouts×2 deterministic reps, seed7/state0, original220active
  budget,8-action model schedule and native grasp/80mm/10mm/20mrad/>1simsec gates.
- Initialattempt001 aborts firstcase409: missednative max5 packet cap.0 policy
  actions applied,5 cases notrun, retained. Verifyneutral5+3 transport/stalereject;
  repairlocal8-action buffering, clearonStop, preservecap5 andmodel/criteria.
- Freshphysical002 completes6/6 nativegoals and5/6 combined physicalStop/hold/
  freshresume. Firstcase nativegoal butno observedqualifiedgrasp trigger staysfail.
  480poll samples: maxlift118.612mm, no bilateralpadgrasp seen; not fulldensecoverage.
- Fiveholds502–525 samples at2ms+polls, minlift80.166–89.282mm, worstmovement
  3.275mm/range18.810mrad. All5 staleactions409 andfreshresume;3 clearlocal3actions.
- 82 realcohortGPUcalls client111.80/270.98/284.47ms median/p95/max; originalactive
  counts100–138. Modelcoldload70.194s/warm7.030s outsideepisodes. No speechclaim.
- Independent6case/raw82serverreply/616nativeselectedaction audit,11coordinator,Ruff,46upstream
  bytespass. Allterminal gripspositive; released/restingplacement unestablished.
- Ownedpolicy/physics exit0; restorelocalGemma4096/1slot/noTTL,Bonsai unchanged,
  public8996 preserved. No modelpromotion/workshop/hardware/generalizationclaim.
- Next: frozenfirstfailure contactreplay, verifystate equivalence; no cohortretuning.
  Full audit: openvla-physical-audit.md; rawdata remainlocal.

- Contactreplay nowcompletes:100 recordedsteps exactlymatch position/joints/time,
  allnativecontact/goal checksagree.2600 samples,365 lifted>=80mm: rightpad365,
  leftpad0, bothfinger-body contacts present; no bilateralgrasp anywhere sampled.
  Peakrender inspected; independentrawauditpasses. No freshinference or retuning.
  Next: camera/proprioception grasp adaptation, not another brake/offset sweep.
