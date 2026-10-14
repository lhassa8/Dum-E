# Assistant restored after WSL restart — October 14, 2026

The speech-enabled camera demo is running again on port **8996**. Six fresh full
saved-stream journeys pass the original physical, state, cancellation and native
Windows speech judges. This restores a currently tested service; it does not
complete the sustained goal or establish room-microphone performance.

Initial inspection found no assistant, native simulator or MCP listeners in the
restarted WSL environment. The checkout was clean at `25201a1`. Bonsai remained
loaded from the preceding comparison; camera Gemma was absent. The local cached
Q4_K_M Gemma checkpoint was selected explicitly from the CLI's local/linked menu
and verified with a null remote-device identifier. No Mac inference was used.

## Current launch

From the repository root, with the local LM Studio models loaded:

```powershell
powershell.exe -NoProfile -File .\extensions\workbench\scripts\launch_windows.ps1 -CameraTools -BrowserPort 8996 -SimPort 8995 -McpPort 8805 -AsrEdgeTrim -CpuStop -WindowsSpeech
```

Both `prism-ml/bonsai-27b` and `workbench-vision-gemma` are loaded locally with
context 4096, one prediction slot and maximum GPU offload requested. After
qualification, the experiment's one-hour model timers were removed by reloading
without `--ttl`; current metadata reports no TTL. [LM Studio documents this
manual-residency behavior](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict).
This prevents idle model expiry; it does not automatically restart the application
or reload models after Windows/WSL shutdown.

Current restored session is `runs/dume-cb993cb1`. Before the human check it was
Ready with all tools on their racks, CUDA general ASR, explicit CPU Stop, cached
acknowledgment and Microsoft David Desktop WAV output. ASR preparation/warmup
were 3.557/2.631 seconds before recording became available. Open
http://127.0.0.1:8996, enable Listen while working, then start the microphone
yourself. The agent never clicked Speak or granted microphone access.

## Requalification

The initial restored session passes the existing typed camera sequence:
screwdriver fetch, conversation during motion, Stop, resume, change to wrench
with screwdriver return first, and contextual wrench return. HTTP Stop to
observed stopped state was 71.06 ms in this one typed trial; that excludes speech.

A natural saved Windows speech request then passes from the continued returned
scene without object reset. CUDA recognition takes 174.86 ms; native decision
takes 517.82 ms from its own request receipt, pickup starts at 2.494 seconds,
delivery completes at 22.056 seconds. Observed lift is 214.3 mm, handoff error 22.8 mm,
and physical return passes. These separate stage clocks do not establish
last-spoken-word-to-decision latency.

With only 1.5 GB GPU memory free, that idle service was gracefully closed while
the same profile ran on isolated 9036/9035/8806. Only the generated-stream probe
page was opened; its recorder receives synthetic MediaStreams. Its native
renderer, local VAD, ASR, Bonsai/Gemma, task bus and actual physics all participate.
The unchanged protocol SHA is
`b3bd58dd3d97bf68c7f8259e6aa2f492e0c888da0ca8424593e586c63a32e6a1`.

Each of the six original gain/noise cases performs natural voice fetch, a camera
question during motion, Stop and full spoken confirmation, Proceed to resume,
verified delivery, a second Proceed that must not start another pickup, and
contextual return with spoken confirmations. Objects reset only at the protocol's
declared case setup; the actor never receives evaluator object coordinates.

| Fresh qualification | Result |
|---|---:|
| Complete journeys / original cases | 6/6 |
| Verified placements | 12/12 |
| Minimum native-verified lift | 201.35 mm |
| Maximum placement error | 8.47 mm |
| Maximum sampled settled joint drift | 0.000057 rad |
| Maximum sampled held-tool translation | 0.071 mm |
| Native-verified pending camera replies superseded | 5 |
| Conservative Stop cancellation upper bound, median / p95 / max | 762 / 847 / 847 ms |
| Complete required acknowledgments / replies | 24 / 42 |
| Endpoint detection to acknowledgment playing, median / p95 | 51 / 92 ms, n24 |
| Speech API submission to player start, median / p95 | 76 / 129 ms, n67 |

The Stop bounds use the same browser clock and original last-clean-voiced-frame
reference, subtracting only independently verified post-native-ack cleanup.
They do not subtract unsynchronized WSL/Windows clocks. Physical settling is
observed separately over the unchanged 600 ms window. The 35 mm placement, 80 mm
lift, 4 mm neighbor, 0.02 rad drift, 10 mm held-translation and 1000 ms Stop gates
remain unchanged. These are measured samples, not continuous-time guarantees.
One additional playback start was intentionally cancelled; 66 required utterances
finish. Player start/end/media-clock events do not prove acoustic onset or echo.

The combined independent judge passes all six records. The unaltered positive
control passes; five deliberately altered speech records are rejected. The old
helper called all six records "altered"; its output label and earlier prose are
corrected without changing validation logic or original evidence. Relevant
Python regressions pass 38/38; recorder, local-output and observer contracts pass.
All 46 protected upstream files remain byte-identical.

## Restoration checks and remaining work

Temporary test services and their workers are closed, and 8996 is restored.
Two read-only camera questions after the model reload identify all three tools
in 1.474 and 1.024 seconds, with no motion job. They use RGB/catalog input and
conversational pixel estimates. This small probe is not broad layout, long-idle,
or hardware qualification. Other desktop GPU applications were active; no
isolated GPU performance or attribution of the changed timings is claimed.

Raw records, source/PCM identities and rendered frames stay local in
`runs/pc-restart-physical-speech-001`, with typed/saved-delivery traces in
`runs/pc-restart-typed-001` and `runs/pc-restart-voice-001`. The reviewed aggregate
is [pc-restart-requalification-evidence.json](pc-restart-requalification-evidence.json).
The restored service's render was inspected. No hardware, paid service, external
message or microphone recording was initiated.

Human microphone timing, room echo and varied human wording remain open.
Broader camera recovery and the pretrained policy's incomplete Stop/holding
qualification still require work; this camera controller is not a pretrained VLA.
The sustained goal remains active.
