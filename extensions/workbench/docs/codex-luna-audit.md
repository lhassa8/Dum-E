# GPT-6 Luna through the ChatGPT subscription

The user requested using their ChatGPT subscription and Luna 6.0 as Dum-E's host
and model. The official model identifier is `gpt-6-luna`. The existing Codex CLI
0.162.0-alpha.17.2 reports `Logged in using ChatGPT`; real inference calls succeed.
This uses subscription Codex allowance, not API-key billing, and requires an
eligible signed-in account and network access. No new subscription or credits
were purchased. Pricing, quota consumption and usage limits are not estimated
from API prices.

Official sources: [Codex authentication](https://learn.chatgpt.com/docs/auth),
[Luna release](https://learn.chatgpt.com/docs/changelog#codex-2026-09-22-gpt-6-sol-luna),
[non-interactive structured output](https://learn.chatgpt.com/docs/non-interactive-mode),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Run

From `Dum-E/extensions/workbench`:

```sh
WORKBENCH_LANGUAGE_BACKEND=codex uv run --locked dume-sim
```

From the lab root include `--extra assistant --extra dume`. `codex` must be on
PATH, or set `WORKBENCH_CODEX_BIN` to your existing CLI executable. Sign in using
the official `codex login` flow if needed. Existing native simulators cannot switch
models in place; use unused browser/simulator/MCP ports or stop their owning
launcher before changing the backend. The portable default remains MLX; this
optional backend does not silently change another user's authentication choice.

Whisper transcription, microphone capture, Silero detection, Mac speech output,
MuJoCo and physical verification remain local. General request text, the last
eight supplied dialogue messages and simulator observations are sent to OpenAI
through Codex, as authorized by the user's explicit hosting request. Audio and
project files are not included in the inference prompt. No idle microphone
permission or listen scope was expanded.

## Transport and limits

Each model request runs the installed official CLI with an ephemeral session,
a temporary empty workspace, read-only sandbox, isolated user configuration,
replacement Dum-E instructions and the bounded JSON output schema. Shell,
unified execution, code-mode host, apps, plugins, hooks, browser/computer use,
multi-agent, image, workspace dependency, skill-search and memory features are
disabled for this runtime. API-key environment variables are excluded and the
login method is forced to ChatGPT. No login credential is extracted or copied.
Unknown tool-operation events, failed CLI turns, malformed and incomplete output
are rejected; no model or paid API fallback is attempted.

Startup requires an actual read-only inference call. Subsequent probes returned
the correct screwdriver request, multiple-tool clarification and webcam truth
in 2.799–2.990 seconds including CLI startup. Fresh CLI requests currently include
roughly 7,300 input tokens of runtime and instruction overhead. This is a working
integration, not an optimized low-overhead inference service. Subscription
consumption and availability matter for extended use. Local familiar-command
routing avoids this overhead when the existing bounded fast path applies.

Stop remains independent of inference. The existing epoch and interaction
generation checks discard late replies after cancellation. Remote compute may
continue until the CLI exits or the 30-second process timeout; a stopped arm does
not wait for cloud inference. This does not establish hardware stop behavior.

Qualification uses the unchanged 43 distinct requests across four frozen fixture
files, once each to limit subscription consumption. This is a smaller repetition
count than the previous 129-trial studies and does not establish comparable tail
latency or a performance improvement. Results, regressions and runtime evidence
are added below after completion. A live human voice demonstration remains open.

Luna handles conversation and intent selection. The robot's physical controller
remains scripted MuJoCo manipulation; π0.5-LIBERO still requires a separate OpenPi
server and a supported Linux/NVIDIA simulator.

## Recorded result

- All 43 distinct requests pass their existing action/object judges (one trial
  per case). The complete factual-reply suite also meets its ten content criteria
  in a lead-agent reading; this is not human validation. See
  [raw results](codex-luna-evidence.json) for timings and actual replies.
- The first factual suite stopped after one 30-second timeout and a subsequent
  reused HTTP connection reset. The simulator stayed running. Timeout handling
  now returns an explicit request failure; a meaningful regression verifies no
  queued motion and successful next-request recovery. The unchanged ten-case
  suite was rerun and passed; the earlier failure remains in the evidence.
- Full final regressions: 203 lab / 184 fork tests. All 46 protected upstream
  source hashes match. No arm-controller, speech-detector or physics gate changed.
- The main app is running at `127.0.0.1:8766`, using the Luna native simulator at
  `127.0.0.1:8785` and existing Dum-E MCP/task interfaces. The selected model is
  displayed in the browser. Both the model interpretation and actual physics
  verified “I need something for turning screws”: screwdriver placement error
  9.666 mm and observed lift 204.935 mm. This was a typed browser request.
- A pending real Luna reply was superseded by Stop and its task stayed cancelled.
  However the physical Stop smoke test **failed** its post-stop grip/height gate:
  the screwdriver subsequently lay at table height (21.845 mm) with a closed
  gripper command. The native logs and failed snapshot are retained. This is not
  proof that Stop reliably retains tools or that the language backend caused the
  slip. No controller workaround was added. The existing “put it back” recovery
  subsequently succeeded, with 5.211 mm rack placement error.
- Voice output and motion-time listening are restored to their prior ON settings
  after tests, with the microphone idle and all tools on the rack. Live user voice
  qualification, precise mechanical stop timing and the slip fix remain open.
