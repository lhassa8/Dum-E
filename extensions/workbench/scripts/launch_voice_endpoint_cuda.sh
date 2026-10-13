#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export DUME_ASR_DEVICE=cuda
export DUME_ASR_COMPUTE_TYPE=float16
task_asr_libraries="$PWD/.venv-linux/lib/python3.12/site-packages/nvidia"
for library in cublas cudnn; do
  if [[ ! -d "$task_asr_libraries/$library/lib" ]]; then
    echo "Missing verified CUDA speech library: $library; no CPU fallback."
    exit 1
  fi
done
export LD_LIBRARY_PATH="$task_asr_libraries/cublas/lib:$task_asr_libraries/cudnn/lib:$task_asr_libraries/cuda_nvrtc/lib:${LD_LIBRARY_PATH:-}"
exec .venv-linux/bin/python scripts/serve_voice_endpoint_probe.py --local-asr "$@"
