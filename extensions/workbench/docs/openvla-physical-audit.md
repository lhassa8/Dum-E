# Real OpenVLA physical comparison: five of six combined passes

The frozen OpenVLA-OFT cohort completes all six episodes with native task-success
signals; five also meet the original grasp, Stop, dense holding and fresh-resume
criteria. Keep it experimental. One no-trigger episode remains a combined
failure, and these are three known LIBERO layouts repeated twice, not six unseen
tasks. [Aggregate evidence](openvla-physical-evidence.json) preserves every outcome.

This changes strategy after rejected braking corrections: use a different
pretrained policy while retaining the original simulator, controller and judges.
The actor receives RGB front/wrist images,8D robot proprioception and the native
task prompt. Independent simulator object/contact truth belongs to the evaluator;
it is not supplied to the policy. Actual GPU checkpoint inference generates
eight seven-dimensional native OSC actions. No joint-target reinterpretation,
object teleport, hidden weld or model-independent grasp trajectory is used.

## Frozen protocol and retained integration failure

The [prospective protocol](openvla-prospective-protocol.json) predates execution:
tasks0/1/2, two deterministic repetitions, simulator seed7, initial state0,
eight actions per inference,220 active steps including inference waits.
Explicit pauses are excluded. Stop requires observed bilateral native pad grasp
and80mm lift. Holding must last at least2wall seconds and more than1simulated
second, retain grasp and80mm lift, stay within10mm translation and20mrad joint
range. Original joint kp300/damping2 and80/12Nm actuator bounds remain.

Attempt001 stops on an infrastructure error in its first episode: the native
boundary accepts at most five actions per submission, and rejects the model's
eight-action packet with409. I missed this transport constraint before starting.
The report retains1/6 attempted and5 not run; zero policy actions were applied.
It supplies no passing physical data. A neutral-action infrastructure smoke then
checks actual5+3 consumption, eight-action rejection and stale-generation409.

The repair preserves the five-action cap: buffer the model's eight-action chunk
locally and submit five, then three, without another inference. Stop clears both
the native queue and local remainder; resume requests a fresh observation and
inference. The original simulator is closed and a fresh one starts for attempt002.
No model, threshold, budget, controller, prompt or initial state is retuned.
The warmed policy service stays loaded; cold loading is outside episode budgets.

## Completed original-criterion outcomes

| Task/repetition | Qualified Stop | Dense hold | Fresh resume | Native goal | Combined |
|---|---|---|---|---|---|
|0/1|No|Not reached|Not reached|Yes|Fail|
|0/2|Yes|Pass|Yes|Yes|Pass|
|1/1|Yes|Pass|Yes|Yes|Pass|
|1/2|Yes|Pass|Yes|Yes|Pass|
|2/1|Yes|Pass|Yes|Yes|Pass|
|2/2|Yes|Pass|Yes|Yes|Pass|

The five holds include502–525 native callback samples each at2ms intervals, plus
polling samples. Minimum held lift ranges80.166–89.282mm; worst translation is
3.275mm and worst joint range18.810mrad. All retain native bilateral grasp.
Every triggered Stop rejects stale actions and uses fresh post-resume inference.
Three episodes discard a local three-action remainder after Stop. Native task
success occurs in100–138 active steps, below the unchanged220 budget.

In the failed first episode,480 polled observations reach118.612mm sampled lift
but never report bilateral native pad grasp. Polling alone cannot exclude a brief
native-callback grasp. A subsequent frozen-action replay checks that question:
all100 completed-step positions, joints and times match exactly, and every native
grasp/success check matches its source. Across2600 replay samples,365 are lifted
at least80mm. All365 touch the right pad and none the left pad; contacts include
both finger-body geometries. No replay sample reports bilateral pad grasp.
The peak render was inspected. This is evaluator-only contact diagnosis, not
another inference cohort or an altered qualification. It supports correcting
grasp geometry rather than lowering a lift/contact criterion. Raw contact records,
reference checks and audit remain in `contact-diagnosis-001`.

All terminal grip commands are+1. Native goal signals and inspected end images
do not establish released, resting placement. These results are not complete
workshop-tool handoff/return demonstrations, and no spoken Stop latency was
measured. They do not replace the public assistant's separate qualification.
Historical pi0.5 results use a different action schedule and policy RNG design;
this is not a paired causal estimate that OpenVLA improves a given percentage.

## Execution, auditing and restoration

The pinned checkpoint and source identities match the preceding
[GPU qualification](openvla-gpu-qualification.md). The local service rehashes all
checkpoint files, loads BF16 on cuda:0, then warms before opening its endpoint.
This server load is70.194s; discarded warmup7.030s. Across82 actual cohort calls,
client median/p95/max is111.80/270.98/284.47ms; server is108.73/268.29/282.04ms.
Client timing includes HTTP transfer/parse and server processing, excludes
observation capture, speech and motion. Server includes publisher preprocessing,
GPU forward and gripper conversion. Other desktop GPU applications were active.

The independent auditor recomputes all dense physical metrics and full gates,
checks scene IDs, original220 caps, actor/runtime hashes, queue limits, packet
order and fresh-resume times, and matches all82 recorded calls to real server
responses. All616 native selected policy commands match their accepted model
packets, control generations and native step ordinals. Native torque control and
Stop overrides remain authoritative after selection. It excludes the recorded
read-only transport probe and aborted
attempt by a frozen trace offset, not by outcome. Audit passes. Eleven existing
coordinator regressions, changed-helper Ruff and46 protected upstream byte checks
pass. The first-attempt transport smoke is separate from learned-policy evidence.

Only the owned policy and private physics processes were closed; both exited0.
Public8996 remains running. Local Gemma is restored from Q4_K_M cache with4096
context, one slot, requested maximum GPU offload and no TTL; Bonsai stays resident.
No Mac inference, microphone activation, hardware or external messages occur.
Weights, source snapshots, traces, observations and raw actions remain local.

Reproduce with the qualified isolated environments and already pinned checkpoint.
First warm `serve_openvla_local.py` with the same source/preparation/observation
arguments as the inference probe and port8900. Start `libero_runtime.py` on8901
with `--dense-hold-capture`, original OpenPi/config paths and a fresh output.
Do not enable the rejected motion-profile flag. Then, from the extension:

```sh
/home/user/.local/share/dume/libero-py38/bin/python scripts/verify_openvla_physical.py runs/openvla-oft/NEW-PHYSICAL --server-log runs/openvla-oft/server-001/inference.jsonl
.venv-linux/bin/python scripts/audit_openvla_physical.py runs/openvla-oft/physical-002 --server runs/openvla-oft/server-001 --physics runs/openvla-oft/physics-002
```

Choose new output directories for all live processes and supply their actual
server log to the evaluator/auditor. Current raw evidence is under
`runs/openvla-oft/{server-001,physics-002,physical-001,physical-002}`.
Next: use the verified pad/body contact failure to choose a grasp-adaptation
hypothesis that uses camera/proprioception at runtime. Preserve this cohort and
its original criteria; do not sweep corrections against its failed case.
