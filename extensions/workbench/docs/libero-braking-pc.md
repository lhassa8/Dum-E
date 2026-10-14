# Native braking replay audit — 2026-10-14

Higher gains do not qualify holding. Across ten recorded lifted stops, the
unchanged native controller passes4/10 densely sampled windows; doubled damping
and doubled stiffness each pass5/10. Neither alternative is enabled. The original
saved-voice qualification remains2/3.

One frozen grid tests native JointPositionController profiles kp300/damping2,
kp300/damping4 and kp600/damping2. Each receives the exact recorded actions,
initial state and native brake-entry timestamp. Targets are measured robot
joints; torque limits stay at +/-80N·m for joints1–5 and +/-12N·m for joints6–7.
No object state, contacts, or original80mm lift, bilateral-pad grasp,10mm
translation and20mrad joint-range criteria are changed.

The ten windows are all source episodes that reached the lift/contact trigger.
The two source episodes without a qualified grasp remain failures in the earlier
12-episode cohort. This is known-case development replay, not fresh inference,
voice latency, release qualification or held-out generalization. Windows span
just over one simulated second; live wall-clock holding still needs evaluation.

All pre-brake endpoints and captured brake targets match the source exactly.
Baseline held snapshots match within the frozen1e-6 replay tolerance. MuJoCo can
expose two position-cache phases at the same timestamp. The audit retains both
and records which matches each original snapshot; all samples remain in the
physical range/contact calculations.

Denser sampling finds a missed excursion: task2/seed202/baseline reaches
20.309mrad, while earlier polling captured19.978mrad. The earlier4/6 baseline
result remains its as-run snapshot result; it does not prove continuous holding.
Dense replay passes4/10 source windows, versus5/10 from the old polling samples.

The worst baseline reaches31.410mrad, dominated by joint6. Increased damping
reduces it to30.237mrad; increased stiffness to30.282mrad. Both fail. The known
grip-loss window fails with every profile.

A separate unchanged worst-case replay records commanded and clipped torques.
Joint6 requests up to57.333N·m against its12N·m cap and clips on39 of504 captured
callbacks; joint7 clips once. This motivates coordinated torque allocation
within existing limits, not another gain grid. It does not establish that an
allocator will fix grasp loss.

Raw grid: `runs/policy-runtime/braking-replay-003`; torque audit:
`braking-saturation-002`. [Curated evidence](libero-braking-evidence.json) retains
all30 outcomes and raw hashes. Use each run's archived actor for exact source
reproduction; the current helper adds an optional saturation-audit mode.

```bash
/home/user/.local/share/dume/libero-py38/bin/python scripts/probe_libero_braking.py \
  runs/policy-runtime/braking-replay-NEW \
  --source-run runs/policy-runtime/fresh-alignment-001 \
  --physics runs/policy-runtime/fresh-alignment-physics-001/physics.jsonl \
  --openpi runs/policy-runtime/openpi \
  --config-dir runs/policy-runtime/libero-render-001/config
```

Retained setup failures: a reference read after controller construction,
a timestamp map overwriting one cache phase, and a torque-recorder variable
collision. None supplied a candidate comparison. Independent raw checks
recalculate all30 outcomes, match reference snapshots and verify clipping.
The runtime now clears old brake diagnostics on actual scene reset; physics is
unchanged. Existing services/models were preserved. No microphone or hardware
was activated. Next: a separately frozen torque-allocation experiment followed
by prospective fresh-policy evaluation before any promotion.
