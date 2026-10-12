# Local pretrained speech activity detection

Reuse Silero v5 through `@ricky0123/vad-web` **0.0.31** (ISC wrapper, MIT model)
and `onnxruntime-web` **1.22.0** (MIT). `package.json` records dependency identity;
the application uses the publisher's prebuilt browser assets, so npm is not required.

Run `python3 scripts/prepare_speech_vad.py` from the lab or fork extension. It verifies
the immutable registry archive integrity and all six selected asset hashes in
`assets.json`, then saves assets and license notices in `.cache/speech-vad`.
Runtime loads only localhost assets and never downloads weights or sends audio away.
The library does not acquire a microphone during preparation.

`benchmark.html` is an evaluation tool, served only by
`scripts/serve_voice_endpoint_probe.py`. Saved PCM goes through the actual browser
model and, separately, AudioWorklet/MediaRecorder; optional Whisper checks forward
only to the existing local transcription endpoint. They never issue robot commands.
Noisy fixtures and raw recordings remain local. Detailed evidence and limitations:
`docs/speech-detector-audit.md`.

The additional `/physical` judge uses six retained Stop clips during actual
simulated tool carrying and model generation. Its listed simulator API routes
are enabled only with `--physical-checks`. See
`docs/physical-voice-stop-audit.md`; an independent Python verifier reads the
native event log and preserves the published corpus/gates.
