# Full saved-voice arm journeys with native Windows replies

Six complete microphone-free journeys now pass the combined physical, state,
speech and timing checks. Each uses a natural fetch request, a camera question
during motion, spoken Stop, full Stop confirmation, Proceed, verified delivery,
completion-aware Proceed without another pickup, and contextual return. Actual
CUDA recognition, CPU Stop, Bonsai/Gemma, the original task bus, camera-controlled
MuJoCo Panda and native Windows WAV playback participate.

The test uses an isolated service at 9036, never its public microphone page.
Generated streams replace microphone acquisition; the actual recorder and VAD
still run. The user-facing 8996 service was idle and temporarily stopped because
only 935 MB GPU memory was free, then restored afterward. Original four demos
remain running. The rendered test view shows actual simulator frames.

The protected 35 mm placement, 80 mm lift, 4 mm neighbor movement, 0.02 rad settling,
retained grip, 600 ms observation, pending-model supersession and 1000 ms Stop
criteria are unchanged. Browser and WSL wall clocks are not subtracted. Native
Stop is matched by job identity, with the same conservative browser-clock bound
minus verified post-ack cleanup rounded down.

Final run `pc-physical-speech-003`, native `dume-1df075bf`, passes 6/6. All twelve
placements succeed; minimum lift 201.30 mm, maximum placement error 9.26 mm, maximum
settled joint drift 0.002471 rad and held translation 0.392 mm. Five Stops supersede
native-verified pending camera inference. Conservative cancellation upper bounds:
802.25 ms median,965.60 ms sample p95/max, all six below 1000 ms.

All 24 idle-request acknowledgments and 42 ordinary replies finish. Required
complete replies include Stop, delivery, completion-aware Proceed and return.
Acknowledgment detection-to-player start: 64.10 ms median,124.10 ms p95, n=24.
Speech API submission-to-player start: 95.45/151.80 ms, n=66. This separates time
queued behind the neutral cue from synthesis/player startup. It does not measure
the speaker's acoustic onset or room echo. Player media endpoints, WAV duration,
native accepted start/end callbacks and source/PCM identities are checked.
The original duration tolerance is retained; media-clock validation adds another
completion check rather than replacing it.

The initial prepared run001 was not exercised after a scope-label correction.
Run002 failed after one physical delivery/return at the speech observer's
completion wait. Native logs showed completed playback;
that does not turn the failed qualification into a pass. The observer could
replay a reply after an older poll reduced its message count, and did not mark
output superseded before speech API dispatch as cancelled. These gaps were
reproduced independently; the earlier run's precise cause is unproven because
its failure report did not retain the unresolved speech records. The observer now
uses a monotonic count, as the public page does, and records this supersession.
Failure telemetry and media-clock positions were added. Both race checks pass;
the failed run, native logs, rendered screenshot and source snapshot remain local.

Six evidence checks include the unaltered positive control and reject missing speech,
truncated acknowledgment, missing complete Stop confirmation, output failure,
and late acknowledgment. The combined judge first runs the unchanged physical
judge. No source, case, timing target or uncertainty gate was tuned to pass.
This turn changes test tooling, not the production controllers or recognizers.
Recorder/output/observer contracts, Python static checks and 46 upstream-byte
checks pass; the preceding final production regression remains 350 passed.

The restored 8996 service is Ready (`runs/dume-d9410c6e`), with 3.268 s ASR
preparation and 2.146 s warmup before use. Test services and their workers are
gracefully closed. Refresh 8996 and start the microphone yourself for a live check.
Room acoustics, echo, varied real utterances and a convincing human demonstration
remain unverified. This fixed screwdriver cohort is not broad camera-layout or
real-hardware qualification. The full sustained objective remains active.
