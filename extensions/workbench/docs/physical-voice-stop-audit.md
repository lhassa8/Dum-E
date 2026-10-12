# B7: speech models through actual physical Stop — October 12, 2026

Previous goal turn: progress. Pretrained Silero was tested, integrated, published at
fork `7c9c774` / lab `8271aaa`, and observed Ready. This turn verifies the remaining
gap between a recognized Stop callback and cancellation in the actual simulated arm.
No manipulation policy, custom IK, learned-dynamics training or runtime behavior was
added. The pretrained OpenPi demonstration still needs workstation access; the current
project inventory exposes only local Mac projects, and no remote policy job is running.

## Frozen hypothesis and judge

Use the retained six normal/quiet clean/white-noise/hum Stop clips after the retained
spoken “Explain your limitations” question during screwdriver lifting. Expect the
existing independent Stop path to reach native cancellation within the unchanged
1,000 ms boundary while the conversation model generates, without opening the gripper
or creating later work. Live microphone listening and speakers were disabled before
the test and restored afterward.

The protocol was frozen before execution, SHA-256:
`cd330c59d168e8d183f99b20287bc15ae5387567c2a2695a5d19ee92f6435c82`.
All Stop PCM comes unchanged from the earlier 35-case corpus. Question WAV source SHA:
`4b2f0b515d740e3095e59b96bc02c404387b9db0b0cf5e2d3576609ff7f500ef`.
No recordings were captured, no audio played through speakers, and no real robot used.

Actual path: saved PCM → browser AudioBuffer/MediaStream → shipped MediaRecorder and
Silero AudioWorklet → real local Whisper → original Dum-E task bus and native MuJoCo.
The test uses the actual shipped capture controller and speech-detector adapter.
It submits the question through the real conversation model, then plays Stop during
ongoing tool motion. No model calls or physical results are mocked.

An independent Python judge matches native `stop_requested` and `understanding`
events to each trial's active job. It reconstructs the timing reference from the
retained clip manifest and recorded browser source start; it verifies that a model's
first token preceded Stop and its completion followed Stop. Physical snapshots verify
motion, cancellation, grip command, tool height, joint drift and unrelated tools.
Fifteen evidence checks retain the real run but deliberately alter individual fields:
missing/duplicate trials, false timing references, changed protocol, no motion, open
gripper, dropped tool, accepted stale reply, negated Stop, displaced unrelated tool,
unsettled joints and delayed native Stop all fail. The original run still passes.

## Observed outcome

**6/6 trials pass**, including all six independently verified interruptions during
active model generation. End of the retained clean voiced frame to native Stop:

| Clip | Native Stop begins |
|---|---:|
| Normal, clean | 597 ms |
| Normal, white noise | 722 ms |
| Normal, hum | 592 ms |
| Quiet, clean | 588 ms |
| Quiet, white noise | 723 ms |
| Quiet, hum | 629 ms |

Median **613 ms**, sample p95 **722 ms**, maximum **723 ms**. Six samples are not a
population estimate for real workbench acoustics. Timing uses browser source-start
epoch and native wall time on the same Mac; it includes acoustic scheduling/reference
quantization, real browser codec/capture, detection, ASR, local forwarding and native
cancellation dispatch. It is not a human-microphone or audible-response measurement.

Every actual task was cancelled, with no queued/running work afterward. Every pending
reply returned `superseded` and could not become a new task. All two-per-trial capture
tracks ended. Gripper commands remained unchanged and the screwdriver stayed elevated
above the frozen 0.13 m gate through the post-Stop observation.

Joint displacement over the 600 ms observation after the Stopped flag ranged
**0.004563–0.009253 rad**, below the preserved 0.02 rad criterion. This measures residual
motion over that window, not the precise time to complete mechanical settling. A
separate settling-time measurement remains useful. Unrelated hammer/wrench center
displacements remained within the preserved 4 mm limit. These are simulated
surrogate tools; the results do not establish hardware stopping performance.

The same public runtime, exec `46066`, remains live at port 8766. Independently observed
Ready, tools on rack, Speak available, Voice and Listen while working on, microphone
idle. Test tasks retain cancelled status; no physical placement success was claimed.
Screenshots: [trial table](physical-voice-stop-browser.jpg),
[restored assistant](physical-voice-stop-ready.jpg).

## Repeat and limits

This integration judge requires the retained local audio corpus, the normal simulator
running at 8766/8765, and browser automation. Raw audio stays local; a fresh clone does
not contain that corpus. From the lab, with a fresh output directory:

```sh
uv run --locked --extra assistant --extra dume python scripts/prepare_physical_voice_probe.py runs/physical-stop-next
python3 scripts/serve_voice_endpoint_probe.py --physical-checks --clips runs/physical-stop-next
```

Turn off the public app's Voice and Listen while working, then open
`http://127.0.0.1:8772/physical` and use its Run button. Judge afterward:

```sh
uv run --locked --extra assistant --extra dume python scripts/judge_physical_voice_stop.py runs/physical-stop-next --native-log PATH_TO_CURRENT_PHYSICS_EVENTS
uv run --locked --extra assistant --extra dume python scripts/check_physical_voice_judge.py runs/physical-stop-next --native-log PATH_TO_CURRENT_PHYSICS_EVENTS
```

Restore voice controls and leave the simulator Ready. The physical API proxy is disabled
unless `--physical-checks` is explicitly supplied; it exposes only the listed loopback
simulation routes. It adds no public application screen or hardware endpoint.

Application source and dependencies are unchanged from the already tested Silero
commit (187 lab / 168 fork regression checks). New verification scripts pass Ruff and
the retained-run checks. The fork judge is also run on the actual captured corpus;
protected upstream hashes remain unchanged. This is validation progress, not full-goal
completion. Natural room audio, camera/VLA manipulation, physical settling duration,
audible onset and a convincing human live demonstration remain incomplete.
