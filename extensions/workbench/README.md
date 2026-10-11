# Dum-E workbench: local voice and physical simulation

An additive Mac extension for Dum-E: ask for a screwdriver, wrench or hammer,
watch a MuJoCo Panda grasp and deliver it to a green handoff tray, and hear the
assistant respond. Hello/thanks can produce an actual wave/nod. The original
Dum-E task manager, message broker and MCP server run directly from this checkout.
Upstream files are unchanged; this extension replaces the concrete hardware agent
with a simulation implementation of the same interface.

## Run on an Apple Silicon Mac

Python 3.12, uv and ffmpeg are required. This setup was tested on an M5 Mac with
32 GB RAM. It uses a cached Qwen3.6 35B-A3B MLX 4-bit language model (about 20 GB),
plus Whisper small.en (481 MB). No NVIDIA software or cloud API is used.

```sh
cd extensions/workbench
uv sync --locked
# Install ffmpeg if absent: brew install ffmpeg
uv run --locked python scripts/prepare_voice.py
# If not already cached, download the language model:
uv run --locked hf download mlx-community/Qwen3.6-35B-A3B-4bit
uv run --locked dume-sim
```

Open http://127.0.0.1:8766. Click **Speak**, allow microphone access, say
**“Bring me the screwdriver, please,”** then pause. Recording finishes automatically
after 900 ms of quiet following speech; **Finish** remains a manual fallback. Dum-E displays
what it heard, submits the request, speaks and moves the actual simulated arm.
You can also type. Say **“Put it back”** to return the tool.

With **Voice stop on**, the microphone listens only while Dum-E is working. Say
**“stop”** to cancel directly through the physical Stop endpoint, bypassing the
language model. Those clips finish after a 350 ms pause. Other speech is ignored,
including negations such as “don't stop.” Turn Voice stop off to disable motion
listening. There is no always-on idle microphone or wake word.

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
Tool geometry/masses/friction are approximate. Hardware purchases remain deferred.

## Verification

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
```

Tests check original upstream hashes, real simulated grasps/returns/gestures,
honest task outcomes, invalid recordings and transcription isolation. The live
recorder probes also exercise the default browser fetch receiver, not only an
injected network substitute. Real in-app Speak → Finish capture has been observed
to display a recognized utterance and elicit a normal assistant response. The live
voice check separately recognizes an actual saved spoken request, submits it to
the unchanged task bus, and measures physical delivery. Synthetic speech tests
cannot establish accuracy for a user's own microphone or room acoustics.

Automatic completion uses a lightweight waveform energy gate, not a learned speech
activity model. Very quiet speech or continuous room noise may require manual
Finish. Spoken Stop depends on microphone capture, pause detection and local ASR;
the onscreen Stop button remains available independently. The native saved-speech
test reached the Stop endpoint in approximately 0.9 seconds from speech onset and
confirmed cancellation and settled joints; room-dependent timing can differ.

## Structure and provenance

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
