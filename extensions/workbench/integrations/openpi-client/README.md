# Pretrained manipulation: OpenPi connection

The next experiment reuses **π0.5-LIBERO in its supported LIBERO Panda simulation**.
First establish that the published policy works in that environment; then connect
Dum-E's voice and interruption layer and adapt the workbench. This client is the
Mac side of that experiment. It is not a new manipulation model.

**Current status:** the official SDK and wire protocol work locally. Eleven tests
pass, including Stop during a pending request, invalid action rejection and a
stalled SDK worker. No pretrained weights are loaded, no LIBERO rollout has run,
and the current workbench app still uses its existing scripted controller.

## Reproduce the client

Python 3.12 and uv are required. Keep this environment separate from the Robot
lab and the workbench extension: upstream's client requires NumPy <2, whereas
the lab uses NumPy >=2. The Git dependency is pinned to OpenPi commit
`215abfb217dbac7d5f1273282331b9b1866c0479`, with its official client subpackage.
This installs lightweight client dependencies, not CUDA, Torch or model weights.

```sh
# From Robot, or Dum-E/extensions/workbench:
cd integrations/openpi-client
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked python scripts/benchmark_connection.py --output runs/transport-new
```

The benchmark uses the unmodified upstream websocket server with an explicitly
synthetic policy. Its provenance and Apache license are in `fixtures/`. On the
development Mac, 20 warm requests took median/p95 **0.637/0.802 ms**. Five Stops
during 300 ms synthetic inference ended the local request in **21.375/21.872 ms**.
Reconnection plus the next delayed reply took **600.189/605.153 ms**: closing the
client does not preempt server computation. These are transport measurements,
not pretrained model speed, voice latency or physical stopping distance.

## Probe an actual policy server

After a server is available through an authorized connection, probe metadata:

```sh
uv run --locked dume-policy-probe \
  --endpoint ws://127.0.0.1:8000 --output runs/server-probe-new
```

Optionally supply an NPZ of an actual **raw LIBERO observation** and its task:

```sh
uv run --locked dume-policy-probe \
  --endpoint ws://127.0.0.1:8000 --output runs/inference-probe-new \
  --observation-npz /absolute/path/libero-observation.npz \
  --prompt "pick up the bowl"
```

The probe never executes returned actions. Metadata alone does not verify model
identity. An inference failure preserves the observed handshake but exits with
failure and records the error. `model_identity_verified` and
`closed_loop_demonstrated` remain false.

## Observation and action contract

The adapter follows the pinned upstream LIBERO example. It accepts uint8 RGB
`agentview_image` and `robot0_eye_in_hand_image`, flips both image axes, then
resizes/pads to 224×224. Robot telemetry contains a three-value end-effector
position, unit XYZW quaternion, and two gripper positions. The state sent to
OpenPi is eight values: position, axis-angle orientation, and gripper positions.

A LIBERO policy returns an action chunk with seven **OSC controller inputs**.
Those seven values are not Panda joint positions. The current workbench's joint
position interface cannot consume them directly. A real LIBERO adapter must
execute them through LIBERO's configured controller. `LiberoAction` keeps this
representation explicit; there is no automatic workbench mapping.

The wrapper uses the official SDK in a separate local process. Requests have
connection/inference deadlines. Stop invalidates the task generation and queued
actions before terminating blocked client IO. A reply from an older task cannot
populate the new task's queue. This does not stop a physical robot or cancel
remote GPU computation; those require the simulator/robot execution boundary.

## Workstation prerequisite

OpenPi documents Ubuntu 22.04 and NVIDIA inference requirements. Use the existing
RTX 5090 workstation for the policy process after checking its driver, available
Linux/WSL environment, and compatibility with the pinned runtime. Availability
and Blackwell compatibility have not been verified from this Mac chat.

`scripts/workstation_preflight.ps1` is a read-only Windows inventory: it prints
GPU/driver information and existing WSL distributions. It has not run on the
workstation. It installs nothing and changes no permissions.

The maintained LeRobot LIBERO integration explicitly requires Linux. No Docker,
Podman, Colima or Lima executable is available on this Mac. The baseline will run
both LIBERO and the policy on the workstation; the Mac retains the assistant UI
and voice layer. We are not porting an unsupported legacy benchmark to macOS.

The pinned OpenPi x86 Linux lock includes Torch 2.7.1 with CUDA runtime 12.6.77.
PyTorch's documented Blackwell support uses CUDA 12.8 builds. JAX is pinned at
0.5.3; its actual GPU compatibility also needs verification. A matching version
number or visible GPU alone is insufficient evidence that inference will work.
Do not blindly install the default GPU lock on the RTX 5090 or change the pin
without recording and testing the compatibility change.

`scripts/workstation_preflight.py` uses Python 3.11+ standard-library code. First,
run the Windows inventory above. In an existing Linux/WSL environment, inventory
the host without installing any dependencies:

```sh
python scripts/workstation_preflight.py --output runs/linux-inventory-new.json
```

After a compatible inference environment exists, use its Python to run a bounded
32×32 bfloat16 matrix multiplication on the selected GPU backend:

```sh
# In the actual policy environment; no installs happen in this command:
python scripts/workstation_preflight.py --engine jax \
  --openpi-checkout /absolute/path/openpi --output runs/jax-runtime-new.json
# Or choose --engine torch for a PyTorch policy environment.
```

The probe times out after 30 seconds, refuses CPU fallback and preserves previous
reports. On non-Linux hosts it exits with failure before importing either GPU
framework. A passed kernel is runtime evidence only: model identity, checkpoint
loading, full inference and robot task success still need separate checks. The
Linux/GPU branches have not executed on the workstation yet.

The upstream LIBERO Docker example requests privileged execution, host networking
and X11 access. Do not adopt those settings automatically. Prefer a headless
simulator and a policy server restricted to an authorized private connection.
No CUDA software belongs in this Mac environment.

## Next evidence

1. Verify workstation/runtime and exact checkpoint identity before inference.
2. Reproduce a small set of existing LIBERO tasks with independent environment
   success signals, videos and cold/warm inference timings.
3. Connect voice task selection and Stop to that actual simulator, including
   rejection of delayed action chunks and observed settled motion after Stop.
4. Adapt or fine-tune for screwdriver retrieval, return and recovery; compare
   physical outcomes against the preserved workbench criteria. Published
   benchmark performance does not establish screwdriver skill or hardware readiness.

Sources: [OpenPi](https://github.com/Physical-Intelligence/openpi),
[LIBERO example](https://github.com/Physical-Intelligence/openpi/blob/215abfb217dbac7d5f1273282331b9b1866c0479/examples/libero/README.md),
[remote inference](https://github.com/Physical-Intelligence/openpi/blob/215abfb217dbac7d5f1273282331b9b1866c0479/docs/remote_inference.md).

Compatibility sources: [LeRobot LIBERO](https://huggingface.co/docs/lerobot/libero),
[PyTorch 2.7 Blackwell support](https://pytorch.org/blog/pytorch-2-7/),
[JAX changelog](https://docs.jax.dev/en/latest/changelog.html).
