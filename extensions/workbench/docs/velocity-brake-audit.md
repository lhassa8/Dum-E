# Measured-velocity Stop brake rejected — October 14, 2026

Keep the existing policy hold. A frozen short velocity brake passes the same
four of ten recorded Stop windows as baseline and worsens joint excursions.
It is not enabled in `libero_runtime.py` or the public assistant. There is no
fresh-policy or voice qualification for this candidate. The completed replay
provides evidence against the control strategy, rather than grounds for another
parameter sweep.

The previous carrying limiter slowed grasp closure and failed to finish any of
six fresh tasks. This experiment changes the hypothesis: preserve all native
grasp and pre-Stop motion, then apply a torque-feasible brake for one original
policy period (50 ms) after Stop. Both variants capture the same measured joint
goal; after that period the candidate returns to the original kp300/damping2
joint hold. All source episodes and original physical gates remain unchanged.

The controller reads native measured velocity `v`, arm inertia `M`, bias `b`
and original torque bounds. For momentum `p = M v`, select the largest common
rate `r` for which `b - r p` stays within all bounds, capped at the inverse
2 ms physics step. The local model predicts `v_next = (1 - r dt) v`.
No object truth enters the brake. Grip, captured goal and robot clipping are
unchanged. Bias outside the allowed bounds raises an error rather than falling
back. Bounds remain ±80 N·m on joints1–5 and ±12 N·m on joints6–7.

Replay all ten triggered windows from `fresh-alignment-001` once per profile,
using the original Stop time and holding window. Its two no-trigger episodes
remain failures in the original twelve-episode cohort. Twenty trials complete
without errors. Initial state, pre-brake trajectories and entry goals match;
baseline physical metrics reproduce the prior dense baseline within1e-6, with
the same sample counts. This tolerance accounts for small floating-point state
differences and does not change any physical pass threshold.

| Physical outcome | Baseline | Velocity brake |
|---|---:|---:|
| Complete original holding gate | 4/10 | 4/10 |
| Minimum lift at least80 mm | 10/10 | 10/10 |
| Native bilateral grasp throughout | 9/10 | 9/10 |
| Joint range at most20 mrad | 5/10 | 5/10 |
| Translation at most10 mm | 9/10 | 9/10 |

Failures overlap. The candidate's worst range increases from31.410 to38.507 mrad
on task2/seed101 baseline; motion increases from2.390 to9.141 mm. Its existing
grasp-loss episode still loses pad contact and moves14.155 mm. The end render
was inspected, but a plausible-looking held bowl does not override failed
range/contact judges. No candidate or failing episode is discarded.

The independent auditor recalculates all dense physical scores, checks every
preserved actor/helper hash, compares the baseline to prior measurements and
reconstructs all250 brake torques from recorded matrices and velocities. Each
candidate has exactly25 consecutive2ms brake callbacks. All torques respect the
original bounds, and every other recorded callback returns native joint PD.
An initial auditor used bitwise equality for a reconstructed floating-point
rate across NumPy versions; it failed. The correction uses1e-12 relative/absolute
arithmetic tolerance. Raw trajectories and physical gates were not changed.

Added brake computation is median0.048 ms, sample p950.103 ms, maximum0.702 ms
over250 callbacks. This is not a whole-controller real-time guarantee. For240
consecutive braking transitions, maximum-joint one-step velocity prediction
error is median0.000319 rad/s, p950.001012 rad/s and maximum0.001454 rad/s.
The local dynamics approximation is reasonably consistent with these short
measured transitions; that does not establish accurate long-horizon prediction.

The control choice is the problem this trial exposes. A common deceleration
rate is constrained by the most limiting torque component, and this version
omits position correction during the50ms interval. In the worst case its entry
rate is12.141/s, compared with the native nominal damping coefficient69.282/s
before clipping and position terms. This comparison is not a causal ablation
of those terms. Accurate prediction of a poor braking command does not turn it
into good control, and a larger world model would not automatically fix it.

There are no new dependencies. Use the existing isolated LIBERO environment:

```sh
MUJOCO_GL=egl /home/user/.local/share/dume/libero-py38/bin/python scripts/probe_libero_braking.py runs/policy-runtime/NEW --source-run runs/policy-runtime/fresh-alignment-001 --physics runs/policy-runtime/fresh-alignment-physics-001/physics.jsonl --openpi runs/policy-runtime/openpi --config-dir runs/policy-runtime/libero-render-001/config --velocity-brake
.venv-linux/bin/python scripts/audit_libero_velocity_brake.py runs/policy-runtime/velocity-brake-001 --source-run runs/policy-runtime/fresh-alignment-001 --reference runs/policy-runtime/torque-allocation-001/report.json
```

Do not reuse an existing output directory. Aggregate evidence and report hashes
are in [the evidence JSON](velocity-brake-evidence.json); raw traces, source
snapshots, torques and renders remain local under `runs/policy-runtime/`.
Neither local model was unloaded. The replay process exited and created no
persistent listeners. The live8996 demo remains a separate camera-controlled
workbench, with its protected physics and user-controlled microphone preserved.

Next work should distinguish independent joint dissipation and position control
from the failed common-rate assumption, or improve the policy's grasp geometry.
Do not retune this50ms window or raise torque/range limits against these cases.
Any new controller still needs all-case dense replay and prospective full-task
qualification before integration with voice or the public assistant.
