# B6: reuse pretrained speech detection — October 12, 2026

The previous turn was a read-only model audit. It reconfirmed the existing OpenPi
integration and supported Linux/NVIDIA requirement, but did not run a robot model.
This turn makes concrete Mac-side progress using an existing pretrained model.
Workstation access is still the dependency for the primary manipulation demonstration;
custom IK/dynamics work is not resumed as a substitute.

## Decision and observed outcome

Replace the browser's waveform-energy completion detector with pretrained **Silero v5**
through `@ricky0123/vad-web` 0.0.31 and ONNX Runtime Web 1.22.0. Six verified local assets
total 13.68 MB (decimal), including the 2.33 MB model. No new model was trained.

The frozen 35-case protocol combines five retained utterances at normal/quiet gain
with clean audio, stationary white noise and harmonic hum; five controls contain only
silence/noise. RMS detection passed 13/35 and falsely submitted two noise-only clips.
Actual browser WASM Silero probabilities with the shipped pause gate passed **35/35**
with zero noise-only submissions. Warm-cache model loading took 79 ms and frame
inference p95 was approximately 0.20 ms. Virtual-clock completion is not live latency.

Five separate real-time AudioBuffer-to-MediaStream checks exercised the actual browser
recorder, upstream AudioWorklet and capture state machine: **5/5 passed**. The first
version of that judge incorrectly treated the expected no-speech message as failure;
its raw result is retained. The correction admits that specific expected silence
message under the original noise-only-never-submit requirement. The model, fixture
and thresholds were unchanged; a new real-time run passed.

Five further stream checks used the existing actual local Whisper service: **5/5**.
Screwdriver and negated-wrench transcripts were correct, both Stop clips invoked the
strict Stop callback, and noise alone never reached transcription. From the unchanged
last clean voiced-frame reference to callback, noisy Stop took **561 and 696 ms**;
the two ordinary utterances took **1,159 and 1,433 ms**. These include capture/detection,
browser codec, local HTTP forwarding and ASR. They do not measure physical arm settling
or audible acknowledgment and are too few samples for population p95 claims.

The initial 35-case run also passed; the final run uses the exact new
`PauseDetector.sampleProbability` method. Manifest and all 35 PCM hashes were checked
independently after the browser runs. Detailed rows, identities and asset hashes are
in [speech-detector-evidence.json](speech-detector-evidence.json).

## Integration and tradeoffs

- All JS, WASM and model files load from localhost. `startOnLoad:false` preloads weights
  without acquiring audio. The library receives the stream already owned by the
  existing Speak/motion-listening flow and never calls getUserMedia itself.
- Keep the existing 120 ms minimum speech and 900/350 ms request/interrupt pauses.
  Use the library's default positive probability threshold, 0.3. Model classification
  adds roughly 60–200 ms of tail in these fixtures compared with clean energy gating,
  while preventing the tested continuous-noise 12-second waits.
- Recurrent inference is serialized. Cancelled queued frames cannot enter the next
  capture; cleanup waits for outstanding inference and resets state. Recorder cleanup
  handles asynchronous initialization, failures and a five-second startup deadline.
- Missing assets disable Speak with setup guidance; typed requests remain available.
  There is no silent fallback to the failed RMS path. The old energy helper is retained
  for historical comparisons and injected tests.
- No idle microphone listening, wake word, new permission, cloud ASR or CUDA software
  was added. Runtime assets never download from the internet; explicit preparation
  verifies npm archive SHA-512 plus each selected file's SHA-256. ISC/MIT notices included.

The updated public app was independently observed Ready, with Speak enabled and
microphone idle. All six actual served asset hashes match the tested files.
No browser errors/warnings were observed; Voice and Listen while working remain on.

All **187 lab / 168 fork** regression tests pass. Separate Node recorder/adapter
contracts pass, including Stop while dialogue is pending, cancellation during model
setup, stalled startup, preload without audio acquisition, and old-frame isolation.
Ruff passes. All 46 protected upstream file hashes match. Python locks unchanged.

## Reproduce and remaining evidence

Run once in the lab or fork extension:

```sh
python3 scripts/prepare_speech_vad.py
```

Use the normal locked simulator launch. Contract checks:

```sh
node scripts/check_voice_capture.mjs
node scripts/check_speech_detector.mjs
```

Retained local raw audio is deliberately not published. The local benchmark takes a
clip directory with `manifest.json` and the hashed Float32 PCM files:

```sh
node scripts/benchmark_voice_endpoints.mjs runs/voice-endpoint-001
python3 scripts/serve_voice_endpoint_probe.py --clips runs/voice-endpoint-001
```

Open its loopback URL and use the visible evaluation buttons. Whisper stream checks
require the normal assistant running at port 8766. They submit audio only to its
transcription endpoint and never command the arm. Start the test server before opening
its tab; two transient localhost startup/navigation failures were diagnosed without
restarting a process solely because a poll timed out.

Synthetic stationary noise is not a real workbench acoustic test. Silero does not
identify the user's voice or solve speaker echo. Natural sentence pauses, real-room
noise, audible response timing and a human live demonstration remain unverified.
Pretrained arm policy control and physical manipulation adaptation also remain
incomplete. The full assistant goal stays active.

Sources: [Silero VAD](https://github.com/snakers4/silero-vad),
[browser VAD API](https://docs.vad.ricky0123.com/user-guide/api/),
[browser wrapper](https://github.com/ricky0123/vad),
[ONNX Runtime Web](https://www.npmjs.com/package/onnxruntime-web/v/1.22.0).
