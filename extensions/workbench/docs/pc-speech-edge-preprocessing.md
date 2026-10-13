# Late Stop recognition investigation — PC, 2026-10-13

Actual browser capture identified a missed-Stop condition with the current
Whisper input path: speech detection succeeded, but three noisy Stop commands
after five seconds of background audio were rejected by recognition. This is
a reproducible failure separate from the human session; it does not prove the
cause of that session's perceived delay.

The candidate uses the installed maintained Silero VAD to trim only the outer
non-speech edges. It retains every sample between the first and last padded
speech interval, preserving internal pauses and possible negation. It uses the
existing browser threshold 0.3, minimum speech 120 ms and silence 350 ms, with
the library's default 400 ms padding. Whisper weights and its speech/log-probability
confidence gates remain unchanged. No model training or parameter search occurred.

`SpeechInput(edge_trim=True)` enables this experiment; the default is **False**.
It is not enabled in the running assistants. Readiness warmup exercises actual
VAD and CUDA recognition before the experimental service becomes ready.
The implementation is based on the installed faster-whisper 1.2.1 contract,
not inferred defaults in an older README. See the maintained
[VAD implementation](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py).

| Check | Result | Timing boundary |
|---|---|---|
| Current browser VAD, mock ASR | 27/27, no noise-only submissions | Saved word end to callback: Stop median 472.05 ms, p95 545.50 ms, n=12 |
| Current browser VAD + actual CUDA ASR | 24/27; 3 late noisy Stops rejected | Successful Stops only: median 767.20 ms, p95 827.80 ms, n=9; 3 failures retained |
| Edge trim via a separate decode/ASR relay | 27/27 known cases | Stop median 1017.90 ms, p95 2945.30 ms, n=12 including first cold trial; extra decode remains |
| Warm native edge trim + actual CUDA ASR | 26/26 prospective cases | Stop median 779.55 ms, p95 907.80 ms, n=8; no callback above 1 s |

Relay warm Stops alone are 1014.70/1094.50 ms median/p95, n=11. Its first
preprocessing call took 807.99 ms, and the whole first callback took 2945.30 ms;
these are different boundaries, not a causal decomposition. The native candidate
avoids decoding twice and warms its models before readiness: preparation 3.935 s,
spoken warmup 2.007 s. Native preprocessing median/p95/max is 3.5/10/12 ms, n=24.
Detector peak pending frames was one in all completed checks; the baseline's
maximum observed inference was 47.6 ms. No growing queue was observed in this
synthetic cohort. This does not exclude real-room endpoint errors.

The prospective protocol was frozen before inference:
`980265836572f64e42494bb15f43436494a394046573b84985b1441d8ee1f7e6`.
It uses fresh SAPI recordings: Stop now, Don't stop, Please don't stop moving,
Why did you stop, and a natural screwdriver request. Positive Stops start after
2 or 7 seconds, with gains 0.7/0.13 and independently seeded white/hum noise.
All negative/discussion cases retained their meaning and issued zero Stop
callbacks. Noise-only streams submitted nothing. Frozen code and all PCM hashes
passed an independent post-run check; no case filtering or threshold changes.
The initial protocol was
`f033e027286d6dae691fbe04338f66c0d2670bc5022f67148c7839cca678c50f`.

Actual runtime: faster-whisper 1.2.1, CTranslate2 4.8.2, ONNX Runtime 1.31.0;
CUDA FP16 small.en checkpoint `d1d751a5f8271d482d14ca55d9e2deeebbae577f`.
Packaged Silero v6 ONNX SHA-256:
`4cbf549b8326f60f80f2536d9eefeb450a9abe83365a098031c89719f1be17d2`.
The new probe executed actual CUDA inference; no CPU recognition fallback.
Existing demos/renderers and the local language/vision models stayed available.
GPU inventory immediately before the native probe showed 27,824 MiB used,
4,363 MiB free and 6% utilization. This is not a controlled contention study.

Raw reports and synthetic audio remain local in `runs/pc-voice-endpoint-001`,
`pc-voice-endpoint-trim-001`, and `pc-voice-edge-reserved-003`. Failed source
preparations remain in reserved-source directories 001/002: PowerShell 7
synthesis was interrupted after stalling; the unprivileged async attempt emitted
empty files. They were rejected before inference, not counted as speech cases.
The verified installed Windows voice under Windows PowerShell produced source
directory 003. An initial inline CUDA launch failed to load libcublas; the
file-based launcher with verified paths succeeded without device fallback.

Reproduce from the repository extension under WSL, with sufficient GPU headroom:

```bash
bash scripts/launch_voice_endpoint_cuda.sh --port 8989 \
  --clips runs/pc-voice-edge-reserved-003 --trim-speech
```

The browser's local Whisper stream button drives generated MediaStreams through
the shipped recorder and detector. No microphone or speaker output is involved.
The introductory benchmark caption refers to its mock/no-transcription stage;
the local Whisper button actually transcribes, as recorded in each result.
Do not run the same output directory again without preserving its prior report.

The independent judge verifies source/code identity, meaning, positive/negative
Stop routing and callback timing. These results stop at the browser callback:
**native cancellation, physical settling, acoustic latency and human demonstration
remain unqualified**. The next gate is this speech path through actual moving-arm
cancellation and state-correct continuation. Existing speech confidence,
35 mm placement, 80 mm lift and holding criteria remain intact.

Validation for this change: 13 focused Python speech tests, both JS capture/VAD
contracts and Ruff passed. The preceding state/cancellation change's full suite
was 329 passes; it is not substituted for a full-suite run of this candidate.
