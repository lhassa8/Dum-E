#!/usr/bin/env bash
# Separate, local-only pretrained lab. All environments/weights must exist first.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
policy_python="$HOME/.local/share/dume/policy-215abfb/bin/python"
sim_python="$HOME/.local/share/dume/libero-py38/bin/python"
client_python="$HOME/.local/share/dume/openpi-client/bin/python"
for executable in "$policy_python" "$sim_python" "$client_python"; do
  [[ -x "$executable" ]] || { echo "Missing prepared environment: $executable" >&2; exit 1; }
done
for asset in runs/policy-runtime/pi05_libero/checkpoint-objects.json runs/policy-runtime/warmup-001.npz runs/policy-runtime/libero-render-001/config/config.yaml; do
  [[ -f "$asset" ]] || { echo "Missing prepared asset: $asset; see docs/windows-migration.md" >&2; exit 1; }
done
"$client_python" - <<'PY'
import json, socket, urllib.request
for port in (8900, 8901, 8896):
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            raise SystemExit(f'Port {port} is already occupied; no process was stopped')
state=json.load(urllib.request.urlopen('http://127.0.0.1:8876/state', timeout=5))
if state['speech_input']['status'] != 'ready':
    raise SystemExit('Start the workbench and prepare its local speech input first')
PY
output="runs/policy-runtime/interactive-$(date +%Y%m%d-%H%M%S)-$$"
mkdir "$output"
pids=()
cleanup() {
  trap - EXIT INT TERM
  # Shut down our coordinator first, keeping its physics boundary alive.
  for ((i=${#pids[@]}-1; i>=0; i--)); do
    kill -TERM "${pids[i]}" 2>/dev/null || true
    wait "${pids[i]}" 2>/dev/null || true
  done
}
trap cleanup EXIT
trap 'exit 130' INT TERM
await_port() {
  "$client_python" - "$1" "$2" <<'PY'
import os, socket, sys, time
port,pid=map(int,sys.argv[1:])
deadline=time.monotonic()+180
while time.monotonic()<deadline:
    try: os.kill(pid,0)
    except ProcessLookupError: raise SystemExit('Local service exited; inspect launcher logs')
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1',port))==0: break
    time.sleep(.5)
else: raise SystemExit('Service readiness timed out; inspect launcher logs')
PY
}
echo "Preparing actual GPU policy (warmup predictions are discarded). Logs: $output"
"$policy_python" scripts/serve_local_pi05.py --openpi runs/policy-runtime/openpi \
  --checkpoint runs/policy-runtime/pi05_libero --warmup runs/policy-runtime/warmup-001.npz \
  --output "$output/server" > "$output/server.log" 2>&1 &
pids+=("$!")
await_port 8900 "${pids[0]}"
"$sim_python" scripts/libero_runtime.py --openpi runs/policy-runtime/openpi \
  --config-dir runs/policy-runtime/libero-render-001/config \
  --output "$output/physics" > "$output/physics.log" 2>&1 &
pids+=("$!")
await_port 8901 "${pids[1]}"
gateway=$(ip route show default | awk '{print $3; exit}')
"$client_python" scripts/libero_coordinator.py --output "$output/coordinator" \
  --lmstudio-url "http://$gateway:1234" > "$output/coordinator.log" 2>&1 &
pids+=("$!")
await_port 8896 "${pids[2]}"
echo 'Ready: http://127.0.0.1:8896 · microphone off · Ctrl+C closes this lab'
if [[ ${1:-0} != 0 ]]; then
  sleep "$1"
else
  wait "${pids[2]}"
fi
