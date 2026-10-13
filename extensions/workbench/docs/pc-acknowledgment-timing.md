# Neutral acknowledgment timing on Windows

The public UI previously waited for transcription and a complete model decision
before speaking. In six retained natural-fetch cases, the serial server stages
alone took 589 ms median and 1095 ms p95. These are lower bounds that exclude
transport, UI polling and playback; they are not measured acoustic latencies.

The recorder now offers a neutral “Let me check.” at detected completion of an
idle request. It closes capture first, then dispatches acknowledgment without
awaiting it. It does not claim interpretation or task success. Interruption
recordings remain silent until their recognized response, keeping Stop separate.
Voice off suppresses acknowledgment. Cancellation generations protect playback
from late network replies and stale events.
The cue is enabled only when the running backend advertises its prepared audio;
older demos and unavailable assets do not enable it. This does not qualify early
acknowledgment for questions during motion.

Two initial browser-synthesis trials failed before completing a case. The second
captured successful ASR and acknowledgment enqueue, followed by an end event
about 11 ms later without a start event. A direct retained-utterance diagnostic
with explicit English language and an active click also ended after 10 ms without
start; the LocalSpeech wrapper behaved similarly. This isolates the observation
from recording/ASR, but does not prove a browser or operating-system root cause.
Failures and source snapshots remain in `pc-acknowledgment-001/002` and
`pc-tts-diagnostic-001`. Ordinary browser reply playback remains unqualified by
these automated probes; prior human reports do not establish current timing.

The changed strategy generates the fixed acknowledgment once with the installed
Windows SAPI voice, then plays its local WAV with HTMLAudio. The Windows launcher
prepares it when absent. No service, cloud synthesis, recording, binary upload,
or dynamic command execution is added. Ordinary replies retain the existing path.
The API registers the exact phrase and generation before playback, and actual
playing/end callbacks update echo state. A short exact acknowledgment echo is
suppressed only after a real start and for three seconds, including when a newer
reply replaces it. Stop and tool commands remain independent.

The frozen eight-case retry passes independent checks: 37.75 ms median and
56.60 ms p95/max from detected completion to the HTMLAudio playing event. It
includes the first playback on a fresh page. Final saved-word-end to that event
is 1070.00/1111.60 ms, including the existing pause detector. The same-browser
clock measures both ends; source, code, waveform and registered speech generations
are checked independently. No actor or robot command is dispatched by this probe.

The waveform is mono 22050 Hz PCM16, 36257 frames, duration 1.6443 s, generated
by Microsoft David Desktop. Its first 20 ms frame with RMS at least 0.008 ends at
120 ms, so adding that voiced-frame reference gives 157.75/176.60 ms after detected
completion. This still excludes output-device latency and room acoustics.
WAV SHA256:`242f8c3fb568d812db18e71a876c772db4bd85307e43d21e3a7099caca7c1724`.

An actual playback cancellation at about 0.172 s leaves the player paused and
advances only 64 microseconds over the next 250 ms. Contract tests separately cover
unresolved acknowledgment without ASR/Stop blocking, stale completion, duplicate
and stale playback events, denied playback, exact-phrase audio routing, and
time-bounded echo handling. These checks do not establish physical Stop timing;
the preceding six-journey cancellation qualification remains separate.

Raw evidence is local in `runs/pc-acknowledgment-003`. Human acoustic timing,
ordinary audible replies, microphone echo, and a full voice journey with this
acknowledgment still require verification. The sustained goal remains active.

The final overlap test (`pc-acknowledgment-004`) requests another spoken reply as
soon as real ASR finishes, before the cue ends. The latest reply waits for cue
completion without blocking recognition or arm execution; Stop/mute/new speech
invalidate the queue immediately. A two-second output wait limit prevents a
missing end event from indefinitely holding a reply. All eight trials retain
the whole cue: playback durations1682–1720ms, against the1644ms waveform.
Independent registered-generation/source/code checks pass. Completion-to-player
start is33.80ms median and49.30ms p95/max; the first voiced-frame reference adds
120ms, giving153.80/169.30ms before device latency. Final saved-word-end to player
start is1063.10/1123.50ms, including the unchanged pause detector.
Six altered-record checks preserve the original pass and reject a missing case,
an expanded target, an unregistered start, a truncated cue and a late cue. They
ran in WSL after Windows temporary-directory permissions prevented that check;
no original records or permissions were changed.

Full Python regression:346passes in219.03s,one existing dependency warning.
The final additive capability field/API checks pass15tests in4.86s. Recorder,
local output, queued-reply cancellation and VAD contracts pass; Ruff and both
PowerShell parsers pass;46upstream source files remain unchanged. Experimental
8996 is Ready with exact WAV serving, actual CUDA general ASR and explicit CPU
Stop. Recognizer preparation3.619s and warmup2.368s occur before microphone use.
The original four demos remain running. Refresh8996 to load the new frontend;
recording remains human-controlled.
