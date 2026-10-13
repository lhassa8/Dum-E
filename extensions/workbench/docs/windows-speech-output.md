# Installed Windows speech output

Ordinary browser synthesis did not start in the preceding automated tests,
although local WAV playback worked. The new explicit `-WindowsSpeech` option
uses a persistent Windows PowerShell 5/System.Speech worker from WSL to generate
reply WAVs with the installed Microsoft David Desktop voice. The browser plays
those local files and registers actual start/end events. No cloud service,
microphone capture, new package, Windows network listener or direct speaker
output is used by the worker. Default profiles retain their existing backend.

The worker accepts JSON text through standard input, not shell commands. Requests
are limited to 500 characters, synthesis to 10 seconds, output to 2 MB / 45 seconds, and
responses to 3 MB. It warms before native output reports ready. The ASR and physical
Stop routes do not await its worker lock. Configured native failures return 503;
they do not silently switch to browser synthesis. Idle voice readiness waits for
native output; Stop listening during arm work remains independent.

Each reply has a cancellation generation and request identity. If Stop, mute or
a new utterance supersedes synthesis, late audio is discarded. Audio URLs expire
when their generation changes. Playback callbacks report whether their generation
was accepted, and are logged locally. Native speech deadlines use actual audio
duration. Only the neutral acknowledgment holds a subsequent spoken reply;
ordinary replies can supersede previous ordinary audio immediately. Typed Stop
now pauses local playback before sending the interaction request.

The first worker probe generated twelve valid replies without speakers or a
microphone. Startup was 814.48 ms; subsequent text-to-WAV round trips ranged from
18.2 to 64.9 ms. The first real browser/API run completed twelve replies with
66.85 ms median and 100.80 ms p95 from text readiness to HTMLAudio playing.

The final lifecycle run also completes all twelve replies: 67.00 ms median and
100.60ms samplep95/max. Every WAV matches its registered generation, provider,
text and duration; every accepted playback has one start and one end. All whole
utterances finish. A real synthesis result arriving after cancellation is
superseded, exposes no audio URL and writes no WAV; the browser records no late
start. Six altered-record checks reject missing replies, wrong voice, incomplete
playback, late audio advertisement and late playback. Frozen code and raw evidence
remain local in `runs/windows-dialogue-001/002`.

Independent CUDA transcription of the first twelve WAVs matched ten exactly.
Both differences are “stopped task” transcribed as “stop task.” All twelve were
accepted by the unchanged recognition gates. This does not prove perfect speech
content recognition; the mismatches are retained without pronunciation tuning
or relaxed criteria. Browser playback events do not prove acoustic onset, room
echo performance, or that a listener heard the complete reply.

Full final regression: 350 tests pass in 214.74 s with one existing dependency warning.
Native API tests cover Stop while synthesis is blocked, discarded late audio,
expired URLs and failure without fallback. Existing recorder/local-output tests
remain passing. Review also moved active arm cancellation ahead of speech-worker
shutdown; its ordering regression passes. All twelve actual readback transcripts
are rejected by the software echo filter, while Stop, return and new-tool requests
remain accepted. This does not establish microphone/room echo rejection.
The selected local Gemma instance was absent at deployment and
reloaded as `workbench-vision-gemma`,Q4_K_M, 4096 context, one prediction slot;
its loaded path has no remote device identifier. The variant metadata key was
not accepted by the CLI; the listed model key was used and then verified.

Experimental 8996 is Ready with native output, actual CUDA general recognition,
explicit CPU Stop and cached neutral acknowledgment. The actual profile returns
native WAV metadata and serves its audio. First deployment:`runs/dume-d20e0c18`;
final tested deployment:`runs/dume-4db6ecb8`. Recognizer preparation 3.547 s /
warmup 2.312 s happen before recording. Original four
demos remain running. Reproduce the experimental profile from the repository:

```powershell
powershell.exe -NoProfile -File .\extensions\workbench\scripts\launch_windows.ps1 -CameraTools -BrowserPort 8996 -SimPort 8995 -McpPort 8805 -AsrEdgeTrim -CpuStop -WindowsSpeech
```

Refresh the page before a human-controlled microphone check. Full spoken tool
journeys with this output backend, acoustic timing and room echo remain unverified.
The sustained assistant objective remains active.
