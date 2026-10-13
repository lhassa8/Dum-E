#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv-linux/bin/dume-sim ]]; then
  echo 'Prepare the Ubuntu environment with uv sync --locked (UV_PROJECT_ENVIRONMENT=.venv-linux).'
  exit 1
fi
host=$(ip -4 route show default | cut -d ' ' -f3 | head -1)
export MUJOCO_GL=egl
export DUME_ASR_DEVICE=${3:-${DUME_ASR_DEVICE:-cuda}}
export DUME_ASR_EDGE_TRIM=${8:-${DUME_ASR_EDGE_TRIM:-0}}
export DUME_ASR_CPU_STOP=${9:-${DUME_ASR_CPU_STOP:-0}}
export DUME_WINDOWS_SPEECH=${10:-0}
if [[ $DUME_WINDOWS_SPEECH != 0 && $DUME_WINDOWS_SPEECH != 1 ]]; then
  echo 'Windows speech output must be explicitly 0 or 1.'
  exit 1
fi
if [[ $DUME_ASR_CPU_STOP != 0 && $DUME_ASR_CPU_STOP != 1 ]]; then
  echo 'CPU Stop recognizer must be explicitly 0 or 1.'
  exit 1
fi
if [[ $DUME_ASR_EDGE_TRIM != 0 && $DUME_ASR_EDGE_TRIM != 1 ]]; then
  echo 'Speech edge preprocessing must be explicitly 0 or 1.'
  exit 1
fi
if [[ $DUME_ASR_DEVICE == cuda ]]; then
  export DUME_ASR_COMPUTE_TYPE=${DUME_ASR_COMPUTE_TYPE:-float16}
  libraries="$PWD/.venv-linux/lib/python3.12/site-packages/nvidia"
  if [[ ! -d $libraries/cublas/lib || ! -d $libraries/cudnn/lib ]]; then
    echo 'CUDA speech libraries missing. Run uv sync --locked --extra asr-cuda.'
    exit 1
  fi
  export LD_LIBRARY_PATH="$libraries/cublas/lib:$libraries/cudnn/lib:$libraries/cuda_nvrtc/lib:${LD_LIBRARY_PATH:-}"
else
  export DUME_ASR_COMPUTE_TYPE=${DUME_ASR_COMPUTE_TYPE:-int8}
fi
echo "ASR device: $DUME_ASR_DEVICE ($DUME_ASR_COMPUTE_TYPE); no automatic device fallback."
args=(--port 8876 --sim-port 8875 --mcp-port 8801 --language-backend lmstudio --model "${1:-prism-ml/bonsai-27b}" --lmstudio-url "http://$host:1234")
if [[ ${4:-baseline} == camera ]]; then
  args=(--port 8886 --sim-port 8885 --mcp-port 8802 --camera-tools --language-backend lmstudio --model "${1:-prism-ml/bonsai-27b}" --lmstudio-url "http://$host:1234")
fi
if [[ -n ${5:-} || -n ${6:-} || -n ${7:-} ]]; then
  for port in "${5:-}" "${6:-}" "${7:-}"; do
    if [[ ! $port =~ ^[0-9]+$ ]] || (( port < 1024 || port > 65535 )); then
      echo 'Pass three explicit ports between 1024 and 65535.'
      exit 1
    fi
  done
  args[1]=$5; args[3]=$6; args[5]=$7
fi
if [[ -n ${2:-} && ${2:-} != none ]]; then args+=(--vision-model "$2" --vision-coordinates grid1000_yx); fi
exec .venv-linux/bin/dume-sim "${args[@]}"
