# Bounded torque allocation — PC, 2026-10-14

The candidate improves known-window physical passes from4/10 to6/10 but remains
unqualified. No runtime controller is replaced. The original saved-voice
qualification remains2/3; this is not a fresh policy or human microphone test.

After the [saturation audit](libero-braking-pc.md), freeze a new two-profile
experiment on the same ten recorded lifted stops: unchanged kp300/damping2 and
an acceleration-error allocator with identical gains and measured joint target.
The native model produces its ordinary PD/gravity torque command. When that
command exceeds an actuator bound, solve:

`minimize ||M^-1 (tau - native_command)||²`, subject to original torque bounds.

Here M is the native controller's measured-state arm inertia matrix. SciPy1.10.1
bounded-variable least squares uses tolerance1e-9 and at most50 iterations.
Startup imports and a discarded analytic identity-matrix check precede physics.
Commands already within bounds are returned identically. There is no fallback
after solver failure. The robot's original clipping path still enforces +/-80
N·m on joints1–5 and +/-12N·m on joints6–7; no object state or contact parameters
are modified. Model acceleration-error minimization is not a guarantee of grasp
retention or end-effector pose preservation.

All20 replays complete. Every pre-brake state and brake target matches the
source. Baseline physical metrics match the earlier dense grid exactly. Two
previous failures become passes: task0/seed202/offset and task2/seed202/offset.
The four remaining candidate failures are retained:

| Known source stop | Candidate failure |
| --- | --- |
| Next to ramekin /seed202/offset | Pad-contact loss; object motion13.930mm >10mm |
| Table center /seed101/baseline | Joint range25.141mrad >20mrad; lift79.864mm <80mm |
| Table center /seed101/offset | Joint range20.522mrad >20mrad |
| Table center /seed202/baseline | Lift79.416mm <80mm |

The worst joint excursion decreases from31.410 to25.141mrad, but the accompanying
bowl height dips below the protected minimum. None of these failures is rounded
into a pass. Original bilateral-pad,80mm lift,10mm translation,20mrad joint range
and fixed >1sim-second windows remain unchanged; all native callback and endpoint
samples contribute. The two earlier no-trigger episodes remain failures in the
source12-episode cohort and are not holding windows.

Extra computation after native PD calculation: all5,144 candidate callbacks
median/p95/max0.008/0.021/10.732ms. The227 callbacks that actually solve allocation
take0.130/0.397/10.732ms. These are measured CPU costs, including scheduling
outliers, not the complete control callback or hardware deadline qualification.
The maximum exceeds a2ms real-time deadline. No new package or GPU model was
installed; existing services and models were preserved.

Raw `runs/policy-runtime/torque-allocation-001` includes frozen actor/protocol,
all20 results, dense physical samples, pre/post-allocation torques and renders.
[Curated evidence](libero-torque-allocation-evidence.json) records every outcome
and raw hash. Independent checks recalculate physical metrics, verify the20-case
denominator, confirm exact baseline reproduction and bound every candidate
torque. Solver optimality is supported by the inspected algorithm/startup check;
the raw audit does not independently reconstruct every native inertia matrix.

```bash
/home/user/.local/share/dume/libero-py38/bin/python scripts/probe_libero_braking.py \
  runs/policy-runtime/torque-allocation-NEW --torque-allocation \
  --source-run runs/policy-runtime/fresh-alignment-001 \
  --physics runs/policy-runtime/fresh-alignment-physics-001/physics.jsonl \
  --openpi runs/policy-runtime/openpi \
  --config-dir runs/policy-runtime/libero-render-001/config
```

No gain or solver-weight retuning followed the failures. Next change the
hypothesis: assess a torque-aware carrying-speed governor before Stop, with
end-effector/grasp retention constraints. Lower pre-stop momentum may permit
stopping inside the original bounds. This must preserve the220active-step budget,
count slow/failing deliveries, and undergo a frozen prospective fresh-policy
comparison before promotion. No speculative hardware actuation is authorized.
