# LM Studio / LM Link trial

Historical Qwen3.8 trial. The current working session uses
[Bonsai-27B](bonsai-audit.md), with configurable launcher provider/model/endpoint
options and a measured latency improvement. LM Studio now requires an explicit
model choice, and matching server identity before reusing a native simulator.
The following observations preserve the original trial and its limitations.

The user provided `http://127.0.0.1:1234` with Qwen3.8-27B loaded through LM Link.
The endpoint exposes `qwen/qwen3.8-27b`; a real inference call returned the expected
screwdriver intent. LM Studio metadata reports GGUF Q4_K_M, 17,742,040,464 bytes,
131,072 loaded context tokens. The API does not identify the inference device;
the user confirmed that the RTX 5090 PC is selected as the preferred device.
Direct GPU utilization and driver/backend execution remain unmeasured. No device selection, model
download, load settings or other available model was changed.

## Run the optional conversation backend

From `Robot` (or `Dum-E/extensions/workbench`):

```sh
WORKBENCH_LANGUAGE_BACKEND=lmstudio \
WORKBENCH_LMSTUDIO_URL=http://127.0.0.1:1234 \
WORKBENCH_LMSTUDIO_MODEL=qwen/qwen3.8-27b \
uv run --locked dume-sim
```

Choose unused `--port`, `--sim-port`, `--mcp-port` values if another session is
running. A new backend requires a new native simulator process; merely launching
another browser bridge against the existing native simulator cannot switch its
model. The default remains the qualified MLX backend. For authenticated LM Studio
servers set `WORKBENCH_LMSTUDIO_TOKEN` in your process environment, never a URL.

LM Link can forward localhost inference to a preferred remote device:
[official guide](https://lmstudio.ai/docs/developer/core/lmlink). Microphone capture,
Whisper transcription, Silero detection and speaker output remain on the Mac.
With this opt-in backend, request text, the last eight conversation messages and
simulator observations are sent to the user-configured LM Studio server. Audio
is not sent to LM Studio. No idle listening or new microphone permission is added.

## Adapter and qualification

The adapter uses the existing Dum-E instructions and intent parser with temperature
zero, a 320-token limit and `reasoning_effort: none`. Startup requires the selected
model to be listed and complete an actual read-only inference call. LM Studio receives an explicit JSON schema to constrain the response format. Streamed JSON
is assembled and parsed only after a successful complete response. Truncated,
malformed, unknown-action and HTTP-error results fail without retry or switching
models. HTTP connection timeout is five seconds; inactivity/request processing
has a thirty-second inactivity timeout and an elapsed-time check between streamed
lines. This is not a hard thirty-second wall-clock cancellation of remote compute. Stop keeps its existing independent native route,
and the existing epoch check discards late interpretation after cancellation.
Stop invalidates the local request; remote inference may continue until its response
or timeout. Tests cover a delayed remote fetch reply arriving after Stop without any new
motion command being queued. The model's reply never establishes physical success.

First direct inference took 5.670 seconds. Subsequent adapter requests took
2.275–3.709 seconds, before native fixture qualification. These are text-only
timings, not voice latency, audible onset, mechanical settling or GPU utilization.
First-content-token timing is separately recorded; it cannot safely trigger an
action before the complete intent has been parsed.

The frozen native dialogue fixtures and existing regression suite judge this
candidate. Results and disposition are recorded below after completion. The prior
qualified Mac model's frozen study is historical evidence, not a simultaneous
hardware comparison. No performance advantage or remote GPU execution is inferred
from a working HTTP endpoint.

This backend is a conversation/intent model. It does not serve π0.5-LIBERO or
change the scripted MuJoCo controller. Actual pretrained arm control still needs
the separate OpenPi runtime and supported Linux/NVIDIA simulator.

## Recorded result

Structured output passes all 129 action/object trials across 43 distinct requests
(three repeats), median 3.787 seconds and sample p95 5.550 seconds. The preceding
unconstrained candidate failed three context cases with invalid JSON; its pair
study was stopped early and those incomplete results remain visible. No fixture,
timing boundary or acceptance criterion was weakened.

The factual-reply reading found the capabilities response omitted explicit
simulation scope in all three repeats, so passing action/object selection is not
a full factual-quality qualification. The candidate also remained slower than
the previously qualified Mac study, which was not a simultaneous comparison.
It stayed optional. The user subsequently requested the subscription-backed Luna
backend, and the LM Studio trial was stopped without unloading their models or
changing the preferred remote device. See [results](lmstudio-evidence.json).
