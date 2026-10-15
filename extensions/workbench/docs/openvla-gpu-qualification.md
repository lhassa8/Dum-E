# OpenVLA-OFT runs on the local RTX5090 — October 14, 2026

The pinned OpenVLA-OFT spatial checkpoint executes real BF16 inference on this
workstation. Six calls on one saved native LIBERO observation produce finite
8×7 action chunks. Five warmed calls have median99.55 ms and sample p95108.51 ms;
their outputs are identical. This qualifies local execution, not grasping,
interruption, tool delivery or replacement of the working assistant.
The [aggregate evidence](openvla-gpu-evidence.json) preserves provenance and scope.

After two rejected braking strategies, evaluate a different pretrained grasp
policy rather than another gain/window sweep. The [official OpenVLA-OFT project](https://openvla-oft.github.io/)
provides a LIBERO spatial checkpoint and estimates about16 GB for two-camera
inference. That estimate and published task scores are not our physical scores.
The [six-case prospective protocol](openvla-prospective-protocol.json) is frozen
before any rollout: three known layouts, two deterministic repetitions, original
physical hold gates and220 active steps including inference waits. It remains
unexecuted. Seed7 differs from the publisher's seed0, and repetitions are not
independent policy RNG seeds. There is no paired causal comparison with pi0.5.

## Verified checkpoint and runtime

Public checkpoint `moojink/openvla-7b-oft-finetuned-libero-spatial`, revision
`6d0231af0e48c5985f1ff86908f4674b84bc049b`, has21 selected top-level inference
files totaling15,454,694,095 bytes. Every LFS file matches publisher SHA256;
ordinary files match their pinned Git blob identity and have recorded local
SHA256. Merged model shards, action head, proprioception projector, tokenizer,
configuration and dataset statistics are included. Separate LoRA adapter files
are not required by the selected merged-checkpoint inference configuration.
Publisher metadata reports public/ungated and MIT; original attribution stays
with the downloaded source and model card. Weights and raw data remain local.

Source is `moojink/openvla-oft` at `e4287e94541f459edc4feabc4e181f537cd569a8`.
Its required Transformers fork is at `bc339d9ad707454c0c115970db43c260067c61ab`,
version4.40.1. A wheel was built from that pinned tree; its observed archive
hash is in [the source manifest](../integrations/openvla-oft/source-manifest.json).
Rebuild metadata may change the archive hash; pin the source and record each build.

Use a separate Python3.10.20 environment at
`/home/user/.local/share/dume/openvla-oft-cu128`. The existing pi0.5 environment's
Torch2.7.1/cu126 detects the GPU but lacks sm120 kernels. It is unchanged.
The new Torch2.7.1+cu128 and torchvision0.22.1+cu128 support the actual5090;
[PyTorch's release notes](https://pytorch.org/blog/pytorch-2-7/) document Blackwell
support through CUDA12.8. Driver616.92 reports32,607 MiB total GPU memory.
Real BF16 matrix multiplication, convolution, layer normalization and noncausal
attention execute on cuda:0 and pass fixed numerical reference checks. Compiled
architectures include sm120. This is executed-kernel evidence, not GPU visibility.

The inference-only lock keeps timm0.9.10, tokenizers0.19.1, peft0.11.1 and the
custom Transformers source, while changing old Torch2.2 pins for this GPU.
TensorFlow-CPU2.15.1 supplies the publisher's image resize/crop, with NumPy1.26.4.
All87 installed packages pass dependency consistency checks. This is an explicit
platform adaptation, not an exact recreation of the authors' A100 software setup.
Flash Attention2 is not installed or forced; no claim about the selected internal
attention backend or isolated GPU performance follows.

## Inference contract and measured result

The bootstrap imports original model, head, projector, mask and preprocessing
modules while skipping package initializers that pull in unused training data.
One import of `NormalizationType` is redirected to its identical defining enum;
an AST check verifies the original dataset utility imports that same enum.
Initial preprocessing import failed because the VLA package initializer also
imported training datasets; excluding that initializer fixed the import. No
trained architecture, weights, prediction function or normalization math changed.
Model classes and processor load explicitly from pinned local code; remote-code
auto-loading is disabled for the processor. No dlimp/training dataset is needed.

Inputs are native256px RGB front/wrist images rotated180°, publisher resize to224
and90% area center crop, plus8D robot proprioception. L1 head, two images,
proprioception, no FiLM/diffusion and do_sample false match the selected recipe.
The seventh action component follows the publisher's binarization and sign
conversion: model0/1 close/open becomes native+1/−1. The six remaining components
are unchanged native OSC inputs, not Panda joint targets or absolute world poses.
Our adapter exactly matches the publisher's actual conversion functions on128
chunks, preserves inputs and rejects three malformed-output cases.

Actual model parameters are BF16 on cuda:0. Cold model/component load is68.014 s,
excluding preceding checkpoint rehash and module import. First-call warmup is
14.197 s and its actions are discarded. The five subsequent times are108.51,
95.35,99.55,95.71,105.25 ms. They include publisher image processing, tokenizer,
GPU forward and synchronization; observation packing, gripper conversion,
speech, network transport and motion are excluded. Five repeats of one known
observation cannot establish population latency or task accuracy. Other desktop
GPU applications were active. The saved raw action arrays, actor snapshots,
checkpoint identity and timing scope pass an independent audit.

## Setup failures retained and assistant restored

CUDA-only dependency transfers timed out at NVIDIA-hosted URLs. The identical
dependency versions were obtained through official PyPI while Torch came from
the official cu128 index. A redundant full-history fork fetch was stopped; the
already pinned shallow source tree supplied the wheel. The first checkpoint
transport had made progress before replacement with bounded curl requests.
Preserved partials were reused. Its first shard then timed out with curl28;
other shards completed. A separate repair resumed the first shard, verified its
publisher hash, and was copied into the root checkpoint before full verification.
One early subset helper printed expected full-checkpoint bytes alongside a
single-file result; its verified-file record is authoritative. The corrected
helper now prints verified bytes and never marks a subset as a full checkpoint.

The private dense-capture smoke records524 actual2ms callbacks over1.046 simulated
seconds and rejects the experimental motion profile with409. It is measurement
infrastructure evidence, not a lifted-object pass. That owned service exited0.
Scene-generation regression,11 coordinator tests, helper Ruff and46 protected
upstream byte checks pass. The GPU inference process exited0 and sent no actions.

Gemma was temporarily unloaded for model memory and restored from the local
Q4_K_M cache, context4096, one slot, requested maximum offload, no TTL and null
remote-device identifier. Bonsai stayed resident with its same manual settings.
A fresh read-only `/interact` camera question identifies all three tools after
restoration. No microphone or hardware was activated. Public8996 remains separate
from these experiments. No candidate controller is enabled.

## Reproduce from the extension

Use the existing Linux uv executable under `../../../Tools/linux-uv/bin/uv` if
uv is absent from PATH. Clone both repositories into `runs/openvla-oft/source`
and `runs/openvla-oft/transformers` at the manifest's exact commits, using shallow
commit fetches. Preserve existing directories; do not reset another checkout.
Create the separate Python3.10 environment, then install86 locked dependencies:

```sh
uv pip sync --python /home/user/.local/share/dume/openvla-oft-cu128/bin/python --require-hashes --index https://pypi.org/simple --default-index https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match integrations/openvla-oft/requirements-pc.lock
uv build --wheel runs/openvla-oft/transformers --out-dir runs/openvla-oft/wheels
uv pip install --python /home/user/.local/share/dume/openvla-oft-cu128/bin/python --no-deps runs/openvla-oft/wheels/transformers-4.40.1-py3-none-any.whl
uv pip check --python /home/user/.local/share/dume/openvla-oft-cu128/bin/python
```

Install the custom source wheel after the base sync, which intentionally excludes
it. Record its hash. The complete tested local lock also remains in
`runs/openvla-oft/inference.lock`. Check disk, current GPU usage and resident
models before installing/loading; no GPU visibility check replaces real kernels.

```sh
python scripts/prepare_openvla_checkpoint.py runs/openvla-oft/NEW-CHECKPOINT
python scripts/check_openvla_action_contract.py --source runs/openvla-oft/source
/home/user/.local/share/dume/openvla-oft-cu128/bin/python scripts/probe_openvla_cuda.py runs/openvla-oft/NEW-CUDA-PROBE
/home/user/.local/share/dume/openvla-oft-cu128/bin/python scripts/probe_openvla_inference.py runs/openvla-oft/NEW-INFERENCE-PROBE --source runs/openvla-oft/source --preparation runs/openvla-oft/checkpoint-001 --observation runs/policy-runtime/libero-render-001/observation.npz
```

The downloader/contract check use an environment with huggingface_hub/NumPy;
the GPU probes require the isolated environment. Choose fresh probe directories.
The raw native observation comes from the retained simulator lab; it is not a
room-camera recording. Full raw outputs remain under `runs/openvla-oft/`.
Next: actual closed-loop grasp, Stop hold and fresh-resume trials under the frozen
protocol, then voice integration only after the physical/action gates pass.
