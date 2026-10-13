# Windows workstation migration — October 12, 2026

The Windows mandate supersedes the Mac paths and defaults in older documents.
The sustained goal remains active. The working public controller is scripted and
observes simulator object state; camera answers do not supply its grasp targets.
Camera motion remains experimental after its historical 22/24 reserved result.
No hardware has been purchased or actuated.

## Launch on this PC

From the Dum-E repository root in PowerShell:

```powershell
powershell.exe -NoProfile -File .\extensions\workbench\scripts\launch_windows.ps1
```

Open http://127.0.0.1:8876 in Windows Chrome. Start with a typed request. **Speak**
starts a user-controlled microphone clip. **Listen while working** starts off;
turning it on explicitly enables motion-time listening. No idle microphone is
started. **Voice on** uses an installed local English Windows voice; remote
browser voices are rejected. Stop, mute and page departure cancel browser speech,
and a late speech reply cannot restart audio after cancellation.

The launcher detects the Windows host gateway from Ubuntu's route instead of
assuming LM Studio is reachable at Ubuntu's localhost. It uses the verified local
`prism-ml/bonsai-27b` identifier and optional `workbench-vision-gemma` vision alias.
Pass `-Model MODEL_ID` or `-VisionModel ''` to choose a model or disable camera
questions. Ports 8875/8876/8801 avoid an unrelated Windows service on 8765.
LM Studio must already be serving the selected local models. Loading Bonsai here
used maximum GPU offload, 4096 context and one prediction slot.

## Environment reproduction

Windows 11 Pro has approximately 192 GiB RAM, an RTX 5090 with 32607 MiB VRAM,
driver 616.92, and existing Ubuntu 24.04.3 under WSL2. WSL reports 94 GiB RAM.
About 524 GiB was initially free on C: and 1.26 TiB on D:. GPU memory was already
in use by the loaded vision model and desktop applications. These are inventory
observations, not kernel or model compatibility claims.

The fork branch was verified at `31cd447fd95859f388ca53c655e025175df460f0` before
cloning into a new directory; unrelated Unity work was preserved. No old lab
bundle was available or needed to restore the published extension.

Use Linux Python 3.12 and uv 0.10.11, and rebuild from the extension lock:

```bash
cd /mnt/c/path/to/Dum-E/extensions/workbench
UV_PROJECT_ENVIRONMENT=.venv-linux uv sync --locked --extra asr-cuda
.venv-linux/bin/python scripts/verify_upstream_bytes.py --restore-lf
.venv-linux/bin/python scripts/prepare_voice.py
.venv-linux/bin/python scripts/prepare_speech_vad.py
bash scripts/launch_wsl.sh prism-ml/bonsai-27b workbench-vision-gemma
```

`verify_upstream_bytes.py` changes only CRLF conversions whose restored bytes
match the original protected SHA256 values. It refuses arbitrary source changes.
All 46 upstream hashes pass. No physics, placement judges, or lift gates changed.
Use Linux's native filesystem for large policy environments: the initial Windows
mount copy was slow; recreating the identical cached lock on Linux took under a
second. The prototype workbench environment remains separate from those policies.

The non-Mac ASR backend is faster-whisper 1.2.1 / CTranslate2 4.8.2 with the MIT
`Systran/faster-whisper-small.en` checkpoint pinned at
`d1d751a5f8271d482d14ca55d9e2deeebbae577f`. Runtime model loading is local-only.
Uploaded clips retain the original byte, duration, volume and confidence gates.
The packaged imageio-ffmpeg executable replaces the missing system ffmpeg.
CPU INT8 is the explicitly measured initial configuration, not a GPU fallback.
After real CUDA inference and saved-speech physical qualification, the Windows
launcher defaults to CUDA FP16. Use `-AsrDevice cpu` for an explicit CPU run.
The `asr-cuda` optional dependency group separately locks CUDA libraries. The
launcher selects FP16 on CUDA and rejects
unsupported compute types or missing libraries rather than falling back to CPU.

## Established PC evidence

- Final full extension suite: **251 passed**. The final review found and fixed a
  native speech echo-contract regression; 29 focused tests and then the complete
  suite passed. Both original native output and browser start/cancellation
  semantics are preserved.
- Typed and saved Windows synthetic speech both passed the complete existing
  interaction judge. It checked pickup, delivery, change with verified old-tool
  return, cancellation, resume, contextual return, withdrawal, conversation
  during motion, and clarification across completion. Physical steps preserve
  the existing 35 mm placement checks. No false completion was substituted.
- The six saved speech phrases were recognized correctly in all 30 benchmark
  samples. One cold load/decode took 1601 ms; 29 warm samples had median 829 ms
  and p95 909 ms. These exclude capture, pause detection, network, decision,
  acknowledgment, audible output, and motion. Cold excludes downloading weights.
- The fixed 15-case text fixture passed all action/object checks: median 617 ms,
  p95 778 ms. This measures read-only simulator understanding, excluding speech,
  capture, audible output, and motion. It does not re-establish the earlier
  129-case qualification on this PC.
- All 30 CUDA FP16 saved speech samples passed: 29 warm samples had median
  187 ms / p95 209 ms, versus CPU 829/909 ms. First decode/model load was
  10.102 seconds. The shipped readiness warmup exercised real GPU recognition
  before microphone availability; observed preparation/warmup was 2.706/1.822
  seconds with already populated driver caches. A separate cached-library
  six-sample probe passed with warm median/p95 173/178 ms and first decode
  12.346 seconds. Keep these cold conditions distinct. GPU inventory snapshots
  are saved locally; the main CUDA benchmark overlapped the planned vision
  unload during its tail, and the physical CUDA check also ran alongside the
  separate policy qualification. This is not a controlled GPU-contention study.
  The complete saved-speech physical journey judge also passed on CUDA.
- In the saved-speech interaction run, Stop ASR plus HTTP cancellation dispatch
  took 893 ms (one sample), excluding the 350 ms motion-time completion pause.
  This does not establish the one-second final-spoken-word target or settling.
- A separate single saved-Stop probe measured 778 ms ASR HTTP, 11.5 ms Stop HTTP,
  789 ms clip-ready to cancellation response, and another 46 ms until observed
  Stopped. Across 33 samples over 2.017 seconds, maximum held-tool displacement
  was 0.452 mm and maximum joint range 0.000135 rad. The original 80 mm lift
  criterion, resumed delivery and 35 mm return placement checks passed. This
  is one synthetic-audio sample, not median/p95 or live acoustic qualification.
- The corresponding CUDA probe measured 260 ms ASR HTTP, 14.8 ms Stop HTTP and
  274 ms clip-ready to cancellation response, then 49 ms to observed Stopped.
  Across 32 samples over 2.056 seconds, held-tool displacement stayed below
  0.778 mm and maximum joint range was 0.00794 rad. Resume/return and the original
  lift/placement checks passed. Faster recognition stops at an earlier moving
  pose; do not compare these different stopping states as a hold-profile trial.
- Windows Chrome exposed secure-context MediaRecorder and microphone APIs,
  prepared the shipped local Silero assets, and listed local David, Mark and Zira
  English voices. No microphone was activated by the agent. Real room noise,
  echo, live transcription, acoustic onset and the user demonstration remain open.
- A real Chrome tool-card request delivered a screwdriver and a contextual return
  succeeded at 12.7 mm rack placement error. A 45-second video contains 180 actual
  rendered simulator frames. It is a scripted-contact simulation demonstration.
- After restoration, a real Chrome camera question returned a snapshot-based
  answer without submitting motion. It required the existing alternate view:
  two provider calls took 1331/1056 ms (2388 ms combined, excluding other overhead).
  The last-view 1056 ms field must not be reported as complete camera response
  latency. This single smoke check does not establish camera accuracy or the
  two-second target; held-out motion qualification remains unchanged.

Raw traces, generated WAVs, GPU inventory and video stay in ignored local `runs/`:
`pc-typed-001`, `pc-saved-voice-001`, `pc-audio-fixtures-001`, `pc-asr-cpu-001`,
`pc-dialogue-001`, and `pc-browser-demo-001`. General Ruff lint passes. A whole-tree
format check reports eight pre-existing files; changed files are checked separately.
The additional hold evidence is local `pc-stop-cpu-001`; its curated measurements
are in [Windows evidence](windows-migration-evidence.json).

## Pretrained policy continuation

Official OpenPi source is pinned to `215abfb217dbac7d5f1273282331b9b1866c0479`,
with LIBERO submodule `f78abd68ee283de9f9be3c8f7e2a9ad60246e95c`. OpenPi source is
Apache-2.0; keep upstream notices and the checkpoint's original provenance.
The unchanged inference lock is installed at the Linux-only
`/home/user/.local/share/dume/policy-215abfb`; source and raw evidence are in
`runs/policy-runtime`. The GPU preflight rejected CPU fallback:

- JAX/jaxlib/CUDA plugin 0.5.3: actual GPU bfloat16 matrix kernel passed.
- Torch 2.7.1 with CUDA 12.6: actual kernel failed, reporting unsupported sm_120
  and no kernel image. This failure is preserved, not repaired by CPU inference.
- An existing PyTorch 2.11.0+cu130 environment also ran a real GPU matrix
  operation, but it is not substituted for OpenPi's inference environment.

The selected official `gs://openpi-assets/checkpoints/pi05_libero` checkpoint
lists 16 objects totaling 12,439,085,481 bytes. Download preparation records each
immutable GCS generation, verifies GCS CRC32C (composite objects lack MD5), and
records local SHA256 values outside the Orbax checkpoint tree. All 16 objects
were verified and loaded. Partial transfers are not model-ready evidence.
The separate simulator environment keeps original LIBERO/robosuite versions and
uses explicit CPU Torch variants only for simulator support; policy inference
remains GPU JAX. Its generated lock and any compatibility changes stay recorded.
The old `egl-probe` build first lacked CMake, then encountered CMake 4's removal
of pre-3.5 compatibility. Reusing the policy environment's installed CMake with
the documented `CMAKE_POLICY_VERSION_MINIMUM=3.5` built it successfully, without
editing upstream simulator source. Dependency installation and rendered runtime
qualification remain separate checks.

Actual renderer qualification produced two 256x256 uint8 camera views and an
`OSC_POSE` controller from the official scene. Before policy inference, the fixed
protocol selected `libero_spatial` tasks 0/1/2, initial state 0, seed 7, five
actions per replan, and the original 220-step limit. All three reached the
independent LIBERO task success predicate in **103/110/134 steps**, with no
exceptions. These are three spatial variants of placing a black bowl on a plate,
not arbitrary workshop tasks or a broad benchmark success-rate estimate.

The JAX checkpoint loader took 17.453 seconds, excluding imports/runtime setup.
Of 70 real checkpoint inference calls, the first took 31.169 seconds including
compilation; 69 warm calls had median/p95 **106.577/127.382 ms** server inference.
Transport, rendering, capture, speech and motion are excluded. Videos and complete
actions/timings are local `runs/policy-runtime/rollouts-001`. The checkpoint-object
manifest SHA256 is
`450f2d7b90db37ff3db84074fd9a67ba49fba05c1c482c430b1d1c5de8772084`.
The server wrapper forces GPU JAX and binds 127.0.0.1; the official launcher was
replaced because its default is 0.0.0.0. After this bounded evaluation, the policy
server was stopped and the same local Gemma vision model/alias was restored with
4096 context, max GPU offload and one slot. LM Studio confirmed both models on
**Local**. No Mac runtime was used.

Next: integrate actual-policy task selection and Stop through the existing
cancellable client and a LIBERO execution boundary; warm inference before ready.
Keep the public workbench on its dependable scripted controller during that
qualification. Seven LIBERO action values are
OSC controller inputs; never pass them to the workbench as joint positions.
The existing cancellable OpenPi client remains available for the subsequent
voice/Stop integration. The real rollouts establish supported closed-loop policy
execution; the earlier kernel/transport checks alone did not establish it.

## Reproduce the bounded policy experiment

In an Ubuntu shell from the extension directory, use the verified source checkout
or clone the official repository into a fresh ignored experiment directory:

```bash
git clone https://github.com/Physical-Intelligence/openpi.git runs/policy-runtime/openpi
git -C runs/policy-runtime/openpi checkout 215abfb217dbac7d5f1273282331b9b1866c0479
git -C runs/policy-runtime/openpi submodule update --init third_party/libero
cd runs/policy-runtime/openpi
UV_PROJECT_ENVIRONMENT=/home/user/.local/share/dume/policy-215abfb \
  GIT_LFS_SKIP_SMUDGE=1 uv sync --locked --no-dev
cd ../../..
uv venv --python 3.8 /home/user/.local/share/dume/libero-py38
PATH="/home/user/.local/share/dume/policy-215abfb/bin:$PATH" \
  CMAKE_POLICY_VERSION_MINIMUM=3.5 uv pip sync \
  --python /home/user/.local/share/dume/libero-py38/bin/python \
  integrations/openpi-client/requirements-libero-pc.lock \
  --index-strategy unsafe-best-match
uv run --script --python /usr/bin/python3 scripts/download_pi05_checkpoint.py \
  runs/policy-runtime/pi05_libero
/home/user/.local/share/dume/libero-py38/bin/python scripts/probe_libero_simulator.py \
  runs/policy-runtime/fresh-render --openpi runs/policy-runtime/openpi
# Free GPU memory from the local vision model before starting the policy.
# Terminal 1; use a fresh output directory:
/home/user/.local/share/dume/policy-215abfb/bin/python scripts/serve_local_pi05.py \
  --openpi runs/policy-runtime/openpi --checkpoint runs/policy-runtime/pi05_libero \
  --output runs/policy-runtime/fresh-server
# Terminal 2, after the server reports loopback readiness:
/home/user/.local/share/dume/libero-py38/bin/python scripts/run_fixed_libero.py \
  runs/policy-runtime/fresh-rollouts --openpi runs/policy-runtime/openpi \
  --protocol integrations/openpi-client/fixtures/pi05-libero-pc-smoke.json \
  --config-dir runs/policy-runtime/fresh-render/config
```

These commands require an installed Linux uv and compiler (`g++`/`make`), both
inspected before use here. The installed local uv 0.10.11 executable is under the
parent workspace's `Tools/linux-uv/bin`; use that absolute executable if uv is not
on PATH. The simulator lock includes the official CPU wheel index, avoiding the
initial index-omission failure. It freezes all 123 simulator/support packages.
The policy environment uses the upstream lock unchanged. Retain failures and
unrun task IDs; do not tune this protocol or infer a broad success rate from it.

Sources: [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[CTranslate2 release changes](https://github.com/OpenNMT/CTranslate2/blob/master/CHANGELOG.md),
[official OpenPi](https://github.com/Physical-Intelligence/openpi),
[official LIBERO example](https://github.com/Physical-Intelligence/openpi/blob/215abfb217dbac7d5f1273282331b9b1866c0479/examples/libero/README.md).
