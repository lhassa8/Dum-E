# Dum-E workbench: local voice and physical simulation

An additive Mac extension for Dum-E: ask for a screwdriver, wrench or hammer,
watch a MuJoCo Panda grasp and deliver it to a green handoff tray, and hear the
assistant respond. Hello/thanks can produce an actual wave/nod. The original
Dum-E task manager, message broker and MCP server run directly from this checkout.
Upstream files are unchanged; this extension replaces the concrete hardware agent
with a simulation implementation of the same interface.

The next manipulation experiment reuses OpenPi's pretrained π0.5-LIBERO policy in
its supported simulator. The separate [OpenPi client](integrations/openpi-client/README.md)
is pinned and tested for communication/interruption. It has not loaded model
weights or driven a robot; the public app below still uses its existing controller.

The [hardware adaptation plan](docs/hardware-adaptation-plan.md) documents what
can be reused and what must be measured before choosing an arm. Our primitive
61 g hammer and Panda layout do not establish capacity for real workbench tools.
No hardware is selected or operated.

The [Bonsai-27B integration](docs/bonsai-audit.md) uses your loaded LM Studio model
for conversation and general requests. Model selection is configurable:

```sh
uv run --locked dume-sim --language-backend lmstudio --model prism-ml/bonsai-27b
```

Change `--model` to a compatible model ID exposed by your server; `--lmstudio-url`
selects its address. Environment variables remain supported. The earlier
[Qwen trial](docs/lmstudio-audit.md) is retained. Existing native simulators cannot
switch models in place, and reuse requires matching provider, model and endpoint.
This is independent of the pretrained OpenPi arm-control integration; the local
MLX backend remains the portable default.
The [load-settings experiment](docs/bonsai-load-tuning-audit.md) reduces matched
Bonsai text latency from 2.061 s to 0.686 s median with explicit GPU offload and
one prediction slot, while keeping model selection interchangeable.

The [tool contact fix](docs/idle-contact-audit.md) preserves Stop holds and keeps
returned tools stable through 30 simulated minutes, followed by physical re-pickup.
The launcher rejects older native contact profiles; restart the simulator to apply it.

[Camera questions](docs/vision-language-audit.md) use actual simulator images and
a separate pretrained vision model. The current instance is configured with:
`--vision-model workbench-vision-gemma --vision-coordinates grid1000_yx`.
Ask “What do you see?” and expand the snapshot to inspect the image behind its
answer. A second optical view can resolve uncertainty; image estimates are for
conversation and do not supply robot grasp coordinates.

For [GPT-6 Luna with your ChatGPT subscription](docs/codex-luna-audit.md), use
`WORKBENCH_LANGUAGE_BACKEND=codex uv run --locked dume-sim` with an existing
ChatGPT-signed-in Codex CLI. General requests use subscription allowance; speech
capture and physical checks stay local. No separate API key or billing is used.

## Run on an Apple Silicon Mac

Python 3.12, uv and ffmpeg are required. This setup was tested on an M5 Mac with
32 GB RAM. It uses a cached Qwen3.6 35B-A3B MLX 4-bit language model (about 20 GB),
plus Whisper small.en (481 MB). No NVIDIA software or cloud API is used.

```sh
cd extensions/workbench
uv sync --locked
# Install ffmpeg if absent: brew install ffmpeg
uv run --locked python scripts/prepare_voice.py
python3 scripts/prepare_speech_vad.py
# If not already cached, download the language model:
uv run --locked hf download mlx-community/Qwen3.6-35B-A3B-4bit
uv run --locked dume-sim
```

Open http://127.0.0.1:8766. Click **Speak**, allow microphone access, say
**“Bring me the screwdriver, please,”** then pause. Recording finishes automatically
after 900 ms classified as non-speech by the local pretrained Silero detector; **Finish** remains a manual fallback. Dum-E displays
what it heard, submits the request, speaks and moves the actual simulated arm.
You can also type. Say **“Put it back”** to return the most recent tool. After
a stop, **“resume”** continues the interrupted destination; **“put it back”**
returns that tool to its rack, even when still grasped. A Resume button appears
for remembered tasks. Reset clears recovery. Original cancelled tasks stay cancelled;
recovery creates a new task. The remaining path uses current physical measurements,
including the settled offset of a tool between the fingers.

Delivery starts promptly without waiting through decorative movements. Idle
conversation can include brief nods or curious tilts. Gestures stay off during
manipulation and while holding a paused tool; they never imply physical success.

With **Listen while working on**, the microphone listens only while Dum-E is
working. Ask **“What are you doing?”** without interrupting the current task, or
say **“Actually bring me the wrench instead.”** A change returns the old tool to
its rack and checks placement before retrieving the new one. **“Don't bring me
the screwdriver”** withdraws that specific request and returns the tool. Questions
and task changes also work through the enabled text box while the arm moves.

Say **“stop”** to cancel directly through the physical Stop endpoint, bypassing the
language model. Motion-time clips finish after a 350 ms pause. **“Don't stop”**
leaves movement alone. Turn **Listen while working off** to disable motion
listening. There is no always-on idle microphone or wake word. Longer internal
pauses, room noise and the assistant's own speech need further live evaluation;
the current echo filter is a bounded text heuristic, not acoustic echo cancellation.

**Stop** cancels motion, speech, recording and pending browser transcription.
**Cancel recording** discards the recording and suspends automatic listening for
the current movement. Recordings are bounded to 12 seconds in the browser (15
seconds at the server). Microphone tracks close after each clip, when cancelled,
when work ends or when the page is left. Raw audio remains in memory;
recognized text and task results are logged under `runs/`. Recognition and language
inference are local. Model preparation downloads weights from Hugging Face once;
runtime speech recognition uses only cached files.

Use Chrome or Safari if the embedded browser cannot capture a microphone. Allow
microphone access for this localhost page and for the browser in macOS System
Settings → Privacy & Security → Microphone if prompted. Keep **Voice on** for
spoken replies from the Mac's installed `say` synthesizer.

`WORKBENCH_MODEL=/absolute/path/to/compatible/mlx/model` selects another local
language model; it must produce the documented bounded intent JSON. Models other
than the tested Qwen checkpoint need their own evaluation. `DUME_SPEECH_MODEL`
can select an existing MLX Whisper model directory. Default Whisper revision is
`52a88bf6e98b114a210c21bb83e22d6e1505cb73`, pinned in `asr.py`.

`dume-sim --blocks` keeps the earlier colored-block experiment. Change ports with
`--port`, `--sim-port` and `--mcp-port`. If 8766 is occupied, open the running app
or stop its owning terminal process before starting another session.

## What this proves and what comes later

This is a state-observed simulator with bounded language-model intents and
classical scripted manipulation. Physical contact, lift, release and final position
determine success; tools are never teleported or welded to the gripper. The green
tray stands in for the user's pickup location; no human handoff is simulated.
This is not yet a camera-based VLA policy, learned grasping or a real SO-101 driver.

The accepted local model now keeps a bounded memory residency budget on supported
macOS hosts while the app runs. This improves measured idle response behavior;
it can retain substantial RAM. Set `WORKBENCH_KEEP_MODEL_RESIDENT=0` to disable it.
See [the measured residency results](docs/residency-audit.md) for limits, resource
cost, saved-speech/Stop evidence and the still-unverified long-idle conditions.
Tool geometry/masses/friction are approximate. Hardware purchases remain deferred.
The tool scene uses doubled gripper servo stiffness to prevent observed hammer
slip, preserving its original gap mapping and force cap. That measured simulation
setting needs separate calibration on hardware. See `docs/interaction-audit.md`
for the force comparison, rejected approaches and complete interaction evidence.

## Verification

The first measured responsiveness pass uses a strict fast path for complete,
familiar tool commands and retains the local model for other language. Common
saved-speech requests improved from a 2.85-second median to 1.17 seconds (18 trials,
p95 1.94 seconds); all 30 decisions were correct after the fix. This measures real
local recognition and simulator decisions, not live microphone or audible onset.
Tool manipulation starts directly rather than waiting through pre/post nods;
greeting and conversation gestures remain. See `docs/responsiveness-audit.md` for
the benchmark, failure cases, cold behavior and remaining scope.

The latest bounded dialogue revision keeps the tested large model, shortens replies
and clearly identifies simulator observations. All 30 current-UI saved-speech
decisions pass: familiar requests median/p95 1.174/1.247 seconds; general wording
1.688/2.341 seconds. Spoken Stop during a real pending reply reaches cancellation
in 593ms, with grip retained. Full task changes/returns and 122 fork tests pass.
The smaller experimental model selects the right actions but still gives factual
partials, so it is not the default. See `docs/dialogue-revision-audit.md` for retained
failures, measured boundaries, startup/idle limits and actual browser/physics proof.

```sh
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
# Node.js, if installed, checks capture cancellation logic:
node scripts/check_voice_capture.mjs
# With dume-sim running: real spoken audio -> recognized request -> measured delivery
uv run --locked python scripts/verify_voice_delivery.py --output runs/voice-check-001
# Shipped JS controller + native ASR/physics: pause completion, negation and Stop
node scripts/verify_automatic_voice.mjs runs/automatic-voice-check-001
# Enable the shipped conversation callback during the negative Stop probe
node scripts/verify_automatic_voice.mjs runs/conversation-stop-check-001 conversation
# Saved speech, task changes, contextual clarification and observed placements
uv run --locked python scripts/verify_interaction.py runs/interaction-check-001
# Repeat identical saved speech to measure responsiveness before/after a change
node scripts/benchmark_responsiveness.mjs runs/latency-check-001 runs/latency-fixtures-001
# Saved speech -> Stop/recovery tasks -> physical placement, speech and expression
uv run --locked python scripts/verify_recovery_expression.py runs/recovery-check-001
```

Tests check original upstream hashes, real simulated grasps/returns/gestures,
honest task outcomes, invalid recordings and transcription isolation. The live
recorder probes also exercise the default browser fetch receiver, not only an
injected network substitute. Real in-app Speak → Finish capture has been observed
to display a recognized utterance and elicit a normal assistant response. The live
voice check separately recognizes an actual saved spoken request, submits it to
the unchanged task bus, and measures physical delivery. Synthetic speech tests
cannot establish accuracy for a user's own microphone or room acoustics.

Automatic completion now uses pretrained Silero v5 running locally in your browser.
The fixed synthetic-noise comparison improved from 13/35 to 35/35 passing cases;
actual room noise, speaker echo and natural pauses still need live evaluation.
See [the detector audit](docs/speech-detector-audit.md) for recorded-stream/Whisper
checks, timing boundaries and limitations. Stop recognition still depends on ASR;
the onscreen Stop button remains available independently. The native saved-speech
test reached the Stop endpoint in approximately 0.9 seconds from speech onset and
confirmed cancellation and settled joints; room-dependent timing can differ.

## Structure and provenance

The optional camera experiment uses actual simulated RGB/depth to locate primitive
tool handles. D1's historical baseline was 0.67mm p95 position error / 32ms median
capture-to-estimate. D2's geometric fitter improves held-out p95 to 0.257mm while
taking about 60ms. It assumes known colors, handle dimensions and calibration;
it is not arbitrary real-tool recognition. See `docs/camera-perception-audit.md`
and `docs/camera-delivery-audit.md` for versioned evidence and limitations.
No webcam, model download or extra dependency is required:

```sh
uv run --locked python scripts/generate_camera_dataset.py runs/camera-data-new
uv run --locked python scripts/benchmark_perception.py runs/camera-data-new runs/camera-check-new --split heldout
uv run --locked python scripts/benchmark_camera_pipeline.py runs/camera-timing-new
```

D2 also adds a separate camera-informed contact controller. Images and robot
telemetry guide movement; simulator truth is restricted to an external judge.
All 12 varied initial moves and 8 fresh-camera returns physically place the tool,
but the full journey passes only 11/12 cases: a hammer return nudges its neighbor
4.14mm, beyond the unchanged 4mm limit. A straight hammer pilot is refused as a
weak fit. **This controller remains experimental and is not used by the public
voice app.** It reports release as unverified and has limited held-only resume.

```sh
uv run --locked python scripts/verify_camera_delivery.py runs/camera-journeys-new --fixture fixtures/camera_delivery_cases.json --split heldout --return-after-delivery
```

Expect the documented failing full-journey gate in this version. The next fix
addresses carried-tool drift; green unit tests do not establish full acceptance.

`src/physical_ai_lab/assistant`: MuJoCo scene, bounded local-model interpretation,
controller and physics observation server. `src/physical_ai_lab/dume`: original
task/MCP bridge, browser UI, native speech and local ASR. No copy of upstream core
is embedded here: `upstream.py` resolves the enclosing Dum-E checkout.
`upstream-source.json` records the unchanged base revision and source hashes.
Panda assets retain their original license and MuJoCo Menagerie source/provenance
under `assistant/assets/panda/`. This extension's code is MIT licensed.

The companion Robot lab remains our world-model experiment harness. Useful
simulation interfaces and fixes can be proposed upstream independently of this UI
and model choice. Keep feature work on branches and merge upstream deliberately;
the source hash judge must be updated against reviewed upstream changes.
