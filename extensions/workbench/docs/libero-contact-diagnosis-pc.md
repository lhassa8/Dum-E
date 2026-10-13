# Pretrained-policy grasp diagnosis — PC, 2026-10-13

The failed task-0 voice episode carries the bowl with the left finger pad and
the right finger body, rather than both finger pads. The existing native
bilateral-pad grasp predicate therefore remains false during its elevated carry.
This is a contact-geometry finding, not proof of unstable carrying or a reason
to replace the protected grasp judge. The original qualification remains **2/3**.

We replayed the exact 103 applied OSC actions from epoch 1 of
`runs/policy-runtime/execution-boundary-010/physics.jsonl`, including neutral
inference-wait actions. This corresponds to `live-voice-012`, the failed layout
between the plate and ramekin. The replay uses the same supported LIBERO task,
seed 7, initial state 0, ten initialization steps, and original native controller.
It performs no new checkpoint inference. No microphone or hardware was used;
existing services and GPU models were left running.

Every completed replay step matches the recorded object position, robot joint
position, simulated time, grasp predicate and native success. Maximum position
and joint differences are exactly zero at recorded precision. The diagnostic
also samples contact geometry on every native torque callback without changing
its returned torque, object state, action stream, or physics parameters.

Across 2,678 samples, 393 reach at least 80 mm lift. All 393 have contacts with
`gripper0_finger1_pad_collision`, `gripper0_finger1_collision` and
`gripper0_finger2_collision`; none contact `gripper0_finger2_pad_collision`.
These samples span 4.518–5.272 simulated seconds. Maximum lift is 119.446 mm;
maximum lift while the original bilateral-pad predicate holds is 9.526 mm.
Thus faster evaluator polling would not have found an 80 mm bilateral-pad grasp
in this replay. Native placement succeeds, as in the source episode.

The rendered peak-lift frame was inspected locally. Geometry names and actual
contact records, rather than appearance alone, establish the finding. Raw
protocol, samples, step comparisons, report, image and frozen diagnostic source
remain in `runs/policy-runtime/contact-diagnosis-001`. The source physics SHA-256
is `bb119868b212deec99ed3ea3795d413bb22a07a378ade8dec42349680fd9c1a2`.
The diagnostic actor SHA-256 is
`6717981e04e1273074e0770e9b9eede8567901c7cb5415b635fb24016ad5eeae`.

Reproduce using the existing isolated Python 3.8 LIBERO environment:

```bash
/home/user/.local/share/dume/libero-py38/bin/python scripts/diagnose_libero_contacts.py \
  runs/policy-runtime/contact-diagnosis-NEW \
  --physics runs/policy-runtime/execution-boundary-010/physics.jsonl \
  --epoch 1 --task-id 0 --openpi runs/policy-runtime/openpi \
  --config-dir runs/policy-runtime/libero-render-001/config
```

The next useful experiment is a separate, frozen grasp-adaptation or recovery
evaluation that measures finger-pad alignment and actual retention under Stop.
The replay supplies a known diagnostic case; it is not a held-out adaptation
test. Any intervention must preserve action units, independent physics judges,
the 80 mm bilateral-pad condition, original holding bounds, and all failed
episodes. Success on this known trace cannot establish generalization. Changes
to voice interpretation alone cannot correct this measured contact geometry.
