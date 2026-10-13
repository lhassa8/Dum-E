#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 3 ]; then
    echo 'Usage: launch_mink_experiment.sh EXTENSION_PATH RUN_PATH LMSTUDIO_URL' >&2
    exit 2
fi
extension=$1
run_root=$2
lmstudio=$3
repo=$(dirname "$(dirname "$extension")")
python="$extension/.venv-linux/bin/python"
python3 - <<'PY'
import socket
for port in (8895, 8896, 8803):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', port))
        except OSError:
            raise SystemExit(f'Port {port} is occupied; no experimental services started.')
PY
components='/home/user/.local/share/dume/mink-1.3-components'
if [ ! -f "$components/mink-components-ready" ]; then
    installer=$(mktemp -d /tmp/mink-installer-XXXXXX)
    python3 -m venv "$installer"
    "$installer/bin/pip" install --no-deps --target "$components" 'mink==1.3.0' 'qpsolvers==4.13.0' 'daqp==0.10.3' 'scipy==1.18.1' > "$run_root/component-install.log" 2>&1
    touch "$components/mink-components-ready"
fi
reference=$(mktemp -d /tmp/dume-mink-live-296-XXXXXX)
git -C "$repo" archive --format=tar 296cc6f | tar -xf - -C "$reference"
export PYTHONPATH="$components:$reference/extensions/workbench/src:$reference"
export MUJOCO_GL=egl
export DUME_ASR_DEVICE=cpu
export DUME_ASR_COMPUTE_TYPE=int8
echo 'Experimental CPU IK; CPU ASR explicitly selected to preserve existing GPU services.'
native_pid=''
agent_pid=''
cleanup() {
    trap - EXIT INT TERM
    if [ -n "$agent_pid" ] && kill -0 "$agent_pid" 2>/dev/null; then
        kill -TERM "$agent_pid"
        wait "$agent_pid" || true
    fi
    if [ -n "$native_pid" ] && kill -0 "$native_pid" 2>/dev/null; then
        kill -TERM "$native_pid"
        wait "$native_pid" || true
    fi
}
trap cleanup EXIT INT TERM
"$python" "$extension/scripts/launch_mink_native.py" --tools --camera-tools --port 8895 --language-backend lmstudio --model prism-ml/bonsai-27b --lmstudio-url "$lmstudio" --vision-model workbench-vision-gemma --vision-coordinates grid1000_yx --log-dir "$run_root/native" > "$run_root/native.log" 2>&1 &
native_pid=$!
echo "$native_pid" > "$run_root/native.pid"
"$python" - "$native_pid" <<'PY'
import os
import sys
import time
import httpx
for attempt in range(150):
    try:
        os.kill(int(sys.argv[1]), 0)
    except ProcessLookupError:
        raise RuntimeError('Owned experimental simulator exited; no existing service attached')
    try:
        response = httpx.get('http://127.0.0.1:8895/state', timeout=1, trust_env=False)
        response.raise_for_status()
        state = response.json()
        if state['model_status'] == 'ready' and not state['busy']:
            break
    except httpx.HTTPError:
        pass
    time.sleep(0.2)
else:
    raise RuntimeError('Experimental native simulator did not become ready')
PY
"$python" -m physical_ai_lab.dume.app --camera-tools --port 8896 --sim-port 8895 --mcp-port 8803 --language-backend lmstudio --model prism-ml/bonsai-27b --lmstudio-url "$lmstudio" --vision-model workbench-vision-gemma --vision-coordinates grid1000_yx --log-dir "$run_root/agent" &
agent_pid=$!
echo "$agent_pid" > "$run_root/agent.pid"
wait "$agent_pid"
