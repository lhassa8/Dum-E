# R0: reuse pretrained manipulation, October 11, 2026

The user challenged custom low-level control as the project's main path. The
new approach reproduces OpenPi's π0.5-LIBERO policy in its supported simulation,
then adds the retained Dum-E conversational controls. SmolVLA and existing motion
libraries remain adaptation candidates. This changes the implementation method,
not the assistant goal or physical acceptance criteria.

## Observed checkpoint

- The ten unfinished turn-control prototype files were archived with base commit,
  patch and hashes in `research/turn-prototypes-20261011`. Published core source
  was restored. Existing experiments, raw runs and failure evidence are retained.
- Official OpenPi client pinned at `215abfb217dbac7d5f1273282331b9b1866c0479` in a
  separate locked Python environment. Its NumPy 1.26 dependency does not replace
  the lab's NumPy 2 environment. No CUDA or pretrained weights installed on Mac.
- Nine isolated integration tests pass against the unmodified upstream server:
  queued-action invalidation, Stop during delayed inference, new-task isolation,
  invalid chunks, deadlines, deliberately stalled SDK IO, image/pose contract,
  fixture provenance, and honest failed-probe bookkeeping. Ruff passes.
- Actual wire benchmark: 20 warm calls median/p95 0.637/0.802 ms; five Stops
  during 300 ms synthetic calls end local requests in 21.375/21.872 ms. New-task
  reconnection plus a delayed reply takes 600.189/605.153 ms. Remote computation
  may continue. Evidence: `pretrained-integration-evidence.json`.
- Public voice app independently observed Ready at localhost:8766; three tools
  on rack, voice and motion listening enabled. No public controller/UI change.

## Limits and next dependency

The wire fixture is explicitly synthetic. No pretrained model inference, LIBERO
rollout, policy-driven robot motion or physical Stop is demonstrated. The LIBERO
seven-value OSC action contract cannot be sent to our seven-joint position
controller. No inferred model identity is reported.

Workstation access is unknown: this chat exposes no remote shell or existing
SSH configuration. One access-detail question is pending. The read-only Windows
inventory is prepared but has not run. The next slice must verify RTX 5090/Linux
runtime compatibility, checkpoint identity, then supported benchmark rollouts.
The full goal remains active; this is a connection checkpoint only.
