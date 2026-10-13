# Speech interruption under camera-model load — PC, 2026-10-13

Correction after inspecting the retained camera logs: run007 contains two camera
timeouts and four different-model identity rejections. Its six physical/state
journeys remain verified, but it does not establish the intended Gemma workload.
Run008 subsequently stopped after two full journeys when another camera identity
failure surfaced as a409 dialogue error, even though spoken Stop reached native
cancellation. The selected Gemma instance was absent from the loaded inventory.
It was explicitly reloaded and its identity checked by a real camera response
before run009. Camera workload errors now fail the independent qualification;
superseding an unsuccessful worker cannot establish valid vision contention.

GPU speech recognition can miss the one-second Stop objective while the camera
model is active. The complete saved-voice run retained five timing failures out
of six; an independent check found upper-bound median 1144.05 ms and p95
1244.10 ms. All six Stops interrupted actual camera inference. A connection
failure prevented the last journey from finishing. These results remain in
`runs/pc-physical-voice-stop-005`; they are not a qualification pass.

The earlier typed-fetch run completed twelve native placements, but its large
browser report exceeded a 100 KB limit. Its visible Stop POST times were
951/914/1254/1182/1277/1205 ms. The browser screenshot, DOM, native events and
source freeze remain in `pc-physical-voice-stop-001`. It cannot establish the
full independent holding/cancellation verdict. The subsequent partial run
`pc-physical-voice-stop-003` retained its connection failure and two rows.

The PC decoder now uses already-installed PyAV 19.0.1 in memory, with bounded
decoded samples and the original duration, byte-size, finite-value and silence
gates. Across 24 warm saved-WAV decodes, process decoding median/p95 was
184.10/208.85 ms; native decoding was 5.83/11.64 ms. First native decode/import
was 272.70 ms and is exercised before voice readiness. Sample counts match;
maximum waveform difference remains below 1e-5. Raw: `pc-audio-decode-002`.
The old FFmpeg 7 process misidentifies one periodic 48 kHz stereo WAV as MP3.
The stereo test uses its declared PCM as an independent resampling reference,
keeping the same 1e-5 numeric agreement gate. Other speech gates are unchanged.
See the [PyAV audio contract](https://pyav.org/docs/stable/api/audio.html).

A separate explicit CPU Stop recognizer avoids competing with the camera model
for GPU execution. The official
[tiny English checkpoint](https://huggingface.co/Systran/faster-whisper-tiny.en)
is pinned to `0d3d19a32d3338f10357c0889762bd8d64bbdeba`, with all 78,091,917
downloaded bytes checked against publisher LFS/Git identities. It runs actual
CPU INT8 inference; this is not a fallback from a requested CUDA model.

The CPU candidate classified 53 retained saved-PCM cases correctly, with zero
false Stops. Twenty positive Stops took 171.15 ms median and 199.03 ms p95,
including edge preprocessing but excluding browser capture/decoding/dispatch.
Model load was 0.218 s and warmup 0.306 s. This includes negations and questions
containing Stop, but remains a small synthetic corpus with one SAPI voice.
No prompt/hotword, parameter search, training or confidence relaxation was used.
Raw: `cpu-stop-eval-002`; model identities: `cpu-stop-model-001`.

`-CpuStop` is an explicit opt-in. During interrupt-mode recording, only a
confident whole positive Stop can return through this model. Every other
utterance uses the original primary recognizer, including a negation even if
the auxiliary incorrectly marks it positive. Missing auxiliary readiness fails
explicitly. General speech remains on the requested CUDA small.en model.
Both recognizers warm before microphone availability. Unit probes cover a
blocked GPU, negation, and missing auxiliary readiness; they are transport
checks, not claims about real model accuracy.

The full physical protocol preserves the original 1000 ms cancellation,
0.02 rad settled drift, 600 ms observation, elevated-tool, retained-gripper,
no-queue and pending-inference criteria. It additionally checks original
35 mm placement, 80 mm lift and 4 mm unrelated displacement, plus a 10 mm
held-tool translation limit. Natural voice fetch, question, Stop, Proceed,
completion-aware Proceed and contextual return use actual browser recording
of generated streams, real recognizers/models, original task bus and MuJoCo.
No microphone or speakers are used by the qualification.

Browser and WSL wall-clock timestamps diverged by more than a second and cannot
be directly subtracted. Native Stop events are matched by unique active job.
The actual event must occur between browser Stop POST and its successful
acknowledgment; the independent judge requires that conservative upper bound
to meet the unchanged 1000 ms objective. Pending inference is proven by native
start/finish events in its own clock domain. Observer samples are bounded to
250 ms and taken outside the Stop dispatch path. Settling remains separate.

The probe persists every completed row, projects only needed native state,
bounds reports to 2 MB, logs errors locally, and uses a larger backlog with
HTTP/1.1 content lengths. Earlier connection failures are retained; no cause
is asserted merely from later successful requests. Actor/controller gates
were not weakened to accommodate the test infrastructure.

Native audio libraries also exposed unsafe WSL manager forking in a regression
run. Shared-memory managers now use an explicit clean spawned process in the
launcher and contract tests. The preceding full run had 342 passes, one camera
hammer failure without a captured reason, and a child-process segmentation
fault during fork cleanup. Focused camera/manager checks subsequently passed
28 tests with one dependency warning; the camera failure's cause is unproven.

The complete post-spawn regression suite passes 343 tests in 256.07 s, with
one existing dependency warning and no fork warnings.

The CPU-path run completed all six full natural-voice journeys and passed
every physical/state check. Four Stops interrupted native-verified camera
worker requests; pending replies were superseded. Those requests failed and
do not establish execution of the selected vision model. All six resumed, delivered, refused
a new pickup on completion-aware Proceed, and returned correctly. Twelve native
placements passed; minimum observed lift was 201.53 mm and maximum placement
error 9.56 mm. Maximum settled joint drift was 0.000940 rad, held translation
0.865 mm, and pre-Stop observer age 139.6 ms. All captured tracks ended.

The conservative native-cancellation upper bound was median 931.90 ms, sample
p95/max 1012.40 ms, n=6. Five satisfy the 1000 ms bound. The sixth is only
bounded between 925.60 and 1012.40 ms; its actual deadline is unproven, not
proven violated. **The complete timing qualification remains failed.** No
target was relaxed. Precise native cancellation versus acknowledgment/queue
cleanup timing is the next measurement, alongside broader contention checks.
Raw: `pc-physical-voice-stop-007` and `dume-894b5fc8`. Protocol SHA-256:
`89a63463df5a017238686832ab3a32500b4cf62e0ad640e499fce63a00542226`.
All source/PCM hashes passed the post-run check. HTTP/1.1 eliminated the observed
disconnect in this run; it does not establish the earlier failures' cause.

The temporary experimental assistant remains ready at 8996:

```powershell
.\extensions\workbench\scripts\launch_windows.ps1 -CameraTools -AsrDevice cuda -AsrEdgeTrim -CpuStop -BrowserPort 8996 -SimPort 8995 -McpPort 8805
```

The existing 8876/8886/8896/8986 demos remain separate.
The temporary 8996 assistant uses the experimental profile. Full acoustic
latency, acknowledgment, echo and a convincing human-controlled microphone
demonstration remain outstanding. No hardware is operated or purchased.
