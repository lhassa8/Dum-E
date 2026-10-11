# Experimental carry estimator — rejected for default motion

`carry-position-v2-rejected.npz` is our 7,875-parameter NumPy checkpoint,
trained on synthetic MuJoCo trajectories. Its metadata and checksum are in the
adjacent JSON. It is **never loaded automatically**. The explicit verifier flag
is for research comparisons; it does not enable the public assistant.

This estimates a *current* carried-position residual from camera history and
Panda robot telemetry. It does not predict the effects of lowering, contact or
release, and it does not improve full physical journeys. Features depend on
this robot, tool catalog and simulator actuator proxies. It is not transferable
to an SO-101 without new sensing, calibration, data and validation.

`release-outcome-v2-experimental.npz` is the separate action-conditioned future
release ensemble and its simpler baselines. It passes offline prediction
validation, but worsens complete validation journeys (16/18 rigid vs 14/18
learned). It also stays out of the public runtime. See `docs/release-learning-audit.md`.
New test layouts remain unopened pending a validated motion/recovery policy.

Inference requires only NumPy. Fitting and plotting require the lab's locked
PyTorch/Matplotlib environment. See `docs/carry-learning-audit.md` for the fixed
judges, abstentions, negative findings and reproduction commands.
