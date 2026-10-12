# R1: supported simulator and GPU compatibility, October 11, 2026

Previous turn was progress: the isolated official OpenPi client was tested and
published at Dum-E feature-branch commit `6e001e0`. The actual pretrained policy
and supported simulator remain unrun. Workstation access is still unknown; the
single outstanding access question has not been answered.

## Evidence that changes the next action

- LeRobot's current LIBERO documentation explicitly requires Linux. OpenPi also
  documents Ubuntu 22.04 as its supported platform. This Mac has no Docker,
  Podman, Colima or Lima executable. Do not build an unsupported Mac port as the
  new critical path; run both the benchmark simulator and policy on Linux, with
  the Mac retaining voice and UI.
- OpenPi commit `215abfb217dbac7d5f1273282331b9b1866c0479` pins its LIBERO
  submodule at `f78abd68ee283de9f9be3c8f7e2a9ad60246e95c`. That exact source
  was checked out for read-only inspection. Its documented training dependency
  recipe includes old CUDA-specific Torch packages; none were installed.
- Actual pinned OpenPi lock: JAX/jaxlib/CUDA plugin 0.5.3; Torch 2.7.1; Torch's
  x86 Linux CUDA runtime dependency 12.6.77. Official PyTorch Blackwell guidance
  uses CUDA 12.8 builds. This is a compatibility concern, not a measured failure
  on the workstation. JAX compatibility remains unknown; do not infer failure
  solely from its version or mix new dependencies into the existing Mac project.
- New standard-library preflight inventories Linux GPU/driver state and can
  optionally test an actual bounded GPU bfloat16 kernel in an existing policy
  environment. It installs nothing, rejects CPU fallback and keeps model-ready
  and closed-loop claims false even after a successful kernel.
- Real Mac execution with an explicit JAX probe request exits 1 with `withheld`
  before importing GPU frameworks. It also reads the actual pinned lock and
  reports the versions above. Saved in `pretrained-runtime-evidence.json`.
- Eleven isolated client/preflight checks pass. Two new contract checks verify
  that a non-Linux host never invokes a GPU command and that an inventory alone
  never implies model readiness. These do not certify the unexecuted GPU branch.

## Next dependency

Obtain the existing workstation connection, run its read-only Windows/Linux
inventory, inspect the installed driver/WSL/runtime, and test the selected GPU
backend before loading the checkpoint. Record any necessary runtime adaptation
as a separate tested environment. Then run actual supported LIBERO rollouts with
environment success signals, videos and cold/warm timings. Do not substitute
transport checks or a kernel result for model/robot evidence. Full goal active.

Sources: [LeRobot LIBERO](https://huggingface.co/docs/lerobot/libero),
[OpenPi](https://github.com/Physical-Intelligence/openpi),
[PyTorch Blackwell](https://pytorch.org/blog/pytorch-2-7/),
[JAX changelog](https://docs.jax.dev/en/latest/changelog.html).
