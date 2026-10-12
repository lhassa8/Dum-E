# Long-idle dialogue bottleneck, October 11, 2026

Read-only probing of the running accepted model reproduces a substantial delay:
**27.386 seconds** for the first capabilities answer, then **1.113/1.115 seconds**
for the next two. The native `/understand` endpoint does not submit robot jobs,
speak or capture audio; job identity and idle physical state remain unchanged.
All three requests return the same correct, concise capabilities reply.

The first token takes 26.660 seconds on the first request and 0.394/0.395 seconds
subsequently. Generation takes approximately 0.71 seconds each time. Fixed-prefix
caching remains active (1141 cached tokens). The delay therefore precedes ordinary
token generation; it is not a long spoken reply or a new manipulation plan.

The Mac reports 8324.56 MiB swap usage before probing, with substantial compressed
memory. MLX reports a 20.654 GB process peak allocation. Global page/compression
counter deltas are recorded, but cannot attribute paging to this model alone.
Paging, residency or GPU initialization are plausible explanations, not proven
causes. Natural idle length is unknown; caches were not purged, order was not
randomized, and this is not a cold-start distribution or live microphone timing.
Raw OS snapshots remain local under `runs/long-idle-probe-001`; the published
`long-idle-evidence.json` contains bounded timing/profile and counter summaries.

This establishes meaningful Mac-side work despite the pending RTX access detail.
Do not mark the whole goal blocked solely because pretrained manipulation cannot
yet run. Do not solve this by resuming the superseded custom control experiments.

The bounded next comparison uses the existing
[Qwen3.5-9B MLX 4-bit conversion](https://huggingface.co/mlx-community/Qwen3.5-9B-MLX-4bit),
pinned at `938d8919941c6e7efd3c7150eff7fe9d12afa631`. Actual public metadata reports
5,950,221,072 bytes of Safetensors weights, ungated access and an MLX format.
Download only weights/tokenizer/config data, no remote Python code or CUDA.
The installed text backend is used; no camera interpretation is enabled.

Hypothesis: the mid-sized checkpoint reduces memory demands and idle penalties
without the factual omissions that rejected the 4B candidate. This is unproven.
Use sequential model runs, unchanged prompt/sampler/parser and frozen original,
context, pair, reply-quality and saved-speech fixtures. Review actual replies as
well as intent/schema checks. Retain failures; never promote the candidate merely
because it loads or fits in memory. Keep the accepted default until those checks,
physical regressions and observed runtime support a switch.

This is a conversation-model comparison. The pretrained arm-policy experiment
still requires the existing workstation and a verified compatible Linux runtime.
