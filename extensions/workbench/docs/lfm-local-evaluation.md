# Local LFM2.5 dialogue evaluation — October 14, 2026

Keep Bonsai as the current command interpreter. The verified LFM checkpoint runs
locally, but neither predefined configuration qualifies as its replacement:
the existing budget passes 38/93 requests; the larger reasoning budget passes
81/93 and selects six unwanted fetches for unsupported tasks. This is a local
deployment comparison, not a general intelligence or planning benchmark.

The [official model card](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B)
describes a text-only reasoning model with 24B total and 2.45B active parameters.
That makes dialogue and task planning relevant uses for this workbench. It does
not supply camera perception, joint control, or a pretrained grasping policy.
The model's required reasoning makes complete-answer latency a deployment concern.

## Checkpoint and environment

Use the publisher's [QAD Q4_0 GGUF](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF),
pinned to revision `0912d33141f77e10705345a6732bfd83f0252fdc`.
The expected file is `LFM2.5-24B-A2B-QAD-Q4_0.gguf`, 13,578,190,880 bytes,
SHA-256 `d1c03f73ecaf61017d70419eec9e5dc0b05d50ae26c23d522829b934fbabf8a5`.
The entire file passed both byte count and SHA-256 checks. An independent
hash of the imported LM Studio copy also matches. The runtime loaded that exact
copy, identified architecture `lfm2moe`, and performed actual inference.

The workstation is Windows 11 with an RTX 5090, 32,607 MiB reported memory,
driver 616.92. The evaluation client uses Python 3.12.3 in WSL. LM Studio CLI
commit is `dcefd5a`; fresh candidate logs identify the actual CUDA12 llama.cpp
runtime as 2.57.0. Its process also appears in NVIDIA compute-process telemetry.
Full GPU offload is requested, but layer placement and individual kernel execution
were not profiled. Other desktop GPU applications were active.
No models were resident at initial inspection; Bonsai was loaded for this study
with maximum GPU offload requested, context 4,096, one prediction slot.
Gemma camera inference is not running in this comparison.
LFM loaded with the same context and slot settings under `workbench-lfm-eval` in
8.24 seconds. Bonsai remained resident and idle during candidate requests. Whole
GPU memory rose from 9,581 to 23,288 MiB around the load; this is not a per-model
memory measurement because other applications were active.

## Frozen protocol

The three existing dialogue fixtures contain 31 unique requests. Each is repeated
three times, for 93 planned attempts per model/profile. These are repeated known
requests, not 93 independent unseen tasks. Merged fixture SHA-256 is
`aed016fa54905b47478d8181fadd701435dae51fa81a604933bf2ac7dedf4593`.
Observations are a fixed synthetic Ready state with empty positions, locations
and task records. Supplied conversation histories remain unchanged.

Both profiles use the actual `LMStudioLanguage` backend, actual `ToolIntent.parse`,
temperature zero, streaming, and the existing strict JSON intent schema:

- **Existing:** maximum 320 output tokens, `reasoning_effort: none`.
- **Native reasoning:** maximum 2,048 output tokens, `reasoning_effort` omitted
  by an experiment-only HTTP transport. Production backend and parser are unchanged.

The deadline is 30 seconds. Startup requires a real warmup interpretation.
If it fails, all 93 main requests are reported as not run. Otherwise every
request is attempted, including repeats of failures. Truncated output is a
failure, and reasoning or partial JSON never becomes a robot command.
Action/object correctness is separate from the original prose reply-quality
review. Request-to-result timing includes parsing or failure, excludes loading,
speech capture, ASR, speech output, motion and camera inference. Failed responses
are not complete usable answers. Temperature zero follows our consumer contract;
this does not assess the vendor's recommended temperature 0.1 sampler.

## Completed results

| Model/profile | Correct / attempted | Not run | All-attempt median | Sample p95 | Maximum |
|---|---:|---:|---:|---:|---:|
| Bonsai / existing | 93/93 | 0 | 485 ms | 629 ms | 720 ms |
| Bonsai / native reasoning | 78/93 | 0 | 5,305 ms | 16,324 ms | 17,830 ms |
| LFM / existing | 38/93 | 0 | 1,070 ms | 1,246 ms | 1,257 ms |
| LFM / native reasoning | 81/93 | 0 | 1,392 ms | 4,798 ms | 6,525 ms |

The LFM existing profile has 52 truncated replies and three completed but
incorrect answers to the contextual wrench request. Its fast failed responses
must not be presented as usable-answer latency. Requesting `reasoning_effort: none`
did not prevent reasoning from consuming that model's output budget.
The larger-budget LFM run has three truncated capability replies, three answers
instead of fetching the requested wrench after an information exchange, and six
fetches on unsupported shelf assembly or laptop repair requests. The repair reply
admits repair is unavailable but still selects movement, contrary to the existing
all-or-unsupported contract. No experimental intent is connected to an actuator.

Among correct replies only, medians are 485 ms for Bonsai existing, 4,358 ms for
Bonsai native, 736 ms for LFM existing, and 1,322 ms for LFM native. Their sample
p95 values are 629, 10,239, 1,100 and 3,922 ms respectively. Excluding failures
changes the populations, so these figures must be read alongside the denominators.

All 15 Bonsai native-profile failures exhaust the 2,048-token budget in reasoning and
finish with `length`, without a usable intent. They repeat on five cases:
negative fetch, negated Stop, tool-information questions following two different
fetch histories, and the unsupported laptop repair request. This is evidence
against that configuration for this assistant, not a general ranking of reasoning.
Bonsai's existing-profile replies to the 30 quality requests avoid false webcam,
physical hardware, delivery-success and feelings claims. Their style still has
unnecessary capability repetition. Bonsai native replies repeat a technically imprecise
description of a screwdriver's tip as "pointed"; three repair replies never finish.
LFM's native replies correctly remember the supplied hammer conversation and
deny real hardware or an invented delivery. They repeat "In simulation" on
ordinary tool-information and chat replies. The webcam reply denies camera access
but omits the requested explanation that scene positions come from the simulator.
The feelings reply denies emotions, then uses figurative "love helping" language;
its precision could improve. These qualitative notes are not a blanket quality pass.

The independent auditor reparses saved raw replies, checks model identity and
completion status, verifies fixture and as-run actor hashes, accounts for every
planned request, and recomputes statistics. It does not grade prose semantics.
Sequential runs do not isolate external GPU activity or establish contention
with camera inference. A model benchmark does not qualify spoken Stop, resume,
or full physical tool journeys.

The next relevant LFM evaluation would be a separate prospective planning corpus,
with actions reviewed through the existing task/state controller. It should not
retune or relabel these failed cases into passes. Stop and continuation retain
their model-independent paths; switching a text model cannot replace task-state
tracking or physical grasp qualification. This trial makes no claim that LFM
already improves planning. Only the experiment candidate was unloaded after the
test; Bonsai remained resident and the verified checkpoint/cache were preserved.
No simulator demo was running in the restarted WSL environment during this trial.

## Reproduce

Run from the extension with the installed Python environment. Output directories
for benchmarks must be new. The local server must already expose the requested
model ID; these helpers do not load models or start services.
Full provenance and aggregate data are in
[the evidence JSON](lfm-local-evaluation-evidence.json).

```sh
python scripts/prepare_lfm_checkpoint.py runs/lfm-evaluation/checkpoint-001 --direct-http
python scripts/benchmark_lfm_dialogue.py runs/lfm-evaluation/NEW-RUN --model MODEL_ID --url SERVER_URL
python scripts/benchmark_lfm_dialogue.py runs/lfm-evaluation/NEW-NATIVE-RUN --model MODEL_ID --url SERVER_URL --native-reasoning
python scripts/audit_lfm_dialogue.py runs/lfm-evaluation/NEW-RUN runs/lfm-evaluation/NEW-NATIVE-RUN
```

The preparation helper pins before downloading, retains progress, validates each
HTTP range, and verifies final bytes and SHA-256. The ordinary Hub whole-file
transfer stalled before receiving bytes in this session; the bounded direct HTTP
path completed and passed verification. That observation does not establish the
cause of the stall.
Raw reports, full replies, model weights and cached license stay local under
`runs/lfm-evaluation/`. No microphone, webcam or robot hardware is activated.
