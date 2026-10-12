# Camera response alternatives rejected — October 12, 2026

Two bounded pilots failed the existing two-second complete vision-response
target. The working remote Gemma camera-answer path and Bonsai conversation
configuration are retained. Neither candidate was integrated or evaluated on
the ten validation scenes after failing its pilot. These findings close this
latency slice; they do not fix the remaining camera tail or arm-policy dependency.

| Candidate | All-tools pilot | Empty pilot | Accuracy | Decision |
|---|---:|---:|---|---|
| Remote Gemma31, two images in one request | 2.426 s | 1.469 s | 2/2 correct, zero absent-tool false positives | Reject speed qualification |
| Cached Gemma12 on Mac, explicit GPU load, existing bounded second view | 5.232 s | 5.737 s total | 2/2 correct, zero absent-tool false positives | Reject speed qualification; unloaded |

The paired request selects exactly one complete view. Coordinates and presence
cannot be combined across views; evaluation uses only the selected image's
independent segmentation labels. It uses the existing catalog prior and declared
0–1000 Y/X convention. No tool positions, presence labels or evaluation truth
were sent to the model. Raw request/response protocol remains local. The image
interface is supported by [LM Studio](https://lmstudio.ai/docs/python/llm-prediction/image-input);
actual two-image acceptance and outputs were verified against the loaded server.

The Mac candidate was already cached: no download occurred. Memory inspection
reported87% free; LM Studio estimated7.88GiB with4096-token context, maximum GPU
offload requested and one slot. It loaded in2.83s, excluded from response clocks.
The empty-scene total includes both calls; quoting only its2.868s chosen-view
call would omit the first call. Requested offload does not prove individual
kernel placement. Different model sizes and hosts prevent a size-only causal
claim. Two scenes are a pilot, not a general accuracy estimate.

No application code, prompts, physics, dependencies or existing model instances
changed. Temporary Mac weights were unloaded after the failed judge. The prior
269lab/250fork regression result still applies to unchanged application code;
full suites were not repeated for these research notes.

## Current control-runtime prerequisite

The project inventory exposes Mac development projects. LM Link reports the
existing preferred workstation online and the two working models loaded, but
this chat has no supplied workstation shell, policy endpoint or Linux inventory.
No pretrained arm-policy process or rollout is running. The installed Codex CLI
can connect a terminal UI to an existing remote app-server endpoint, as described
in [official OpenAI documentation](https://learn.chatgpt.com/docs/app-server#connect-the-cli-terminal-ui);
no such endpoint was supplied. No remote service, pairing or security change was
created to work around that missing access.

The read-only first check on the5090 PC is PowerShell:

```powershell
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
wsl --list --verbose
```

Or run the existing `integrations/openpi-client/scripts/workstation_preflight.ps1`
from an available checkout. These commands inventory readiness; they install
nothing and cannot establish a working GPU framework, checkpoint or robot policy.
The Ubuntu/WSL availability question remains pending. After readiness and an
authorized execution route are available, continue the supported pretrained
OpenPi/LIBERO benchmark, preserving the camera's22/24 failed qualification and
the full workbench goal. No further custom IK/physics sweep is proposed.

[Curated measurements](vision-responsiveness-probes-evidence.json). Raw synthetic
images, replies and protocol stay in local ignored `runs/vision-pair-001` and
`runs/vision-gemma12-maxgpu-pilot-001`.
