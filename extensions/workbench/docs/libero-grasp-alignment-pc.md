# Bounded grasp-alignment experiment — PC, 2026-10-13

Four of six 3 mm corrections turn the known failed policy trace into a
bilateral-pad lift, physical hold, and successful native placement. The unchanged
baseline still fails the lift/contact trigger. This establishes sensitivity to
grasp alignment in this one recorded episode; it does not qualify an adapter,
demonstrate fresh policy inference, or establish a universal correction.
The original live voice qualification remains **2/3**.

## Frozen experiment

Following the [contact diagnosis](libero-contact-diagnosis-pc.md), freeze one grid:
baseline and +/-3 mm world-frame translations along X, Y and Z. Apply the
correction once, on the last open-gripper action before the first closing action
(source active step 56). Selection uses the recorded gripper-command transition;
the correction does not use object coordinates or contact truth as actor input.
All other recorded actions, including inference waits, are retained until native
task success or the end of the 103-step source sequence. No further grid tuning.

The installed OSC controller was checked directly: normalized translation inputs
scale to 0.05 metres. Thus each 3 mm correction adds +/-0.06 to one translation
input. The corrected input remains within the original controller bounds.
No seven-element OSC vector is interpreted as Panda joint positions. Simulator
objects, contact parameters, torques and grasp judges are not modified.

The evaluator requests a pause only after both native finger-pad contacts and
80 mm lift coexist at a completed step. Holding uses the same native joint
controller as the policy lab (kp300, damping ratio2), through the original torque
clipping path. Measurements include every native torque callback, not just
rendered frames. The remaining **recorded** actions resume afterward; the learned
policy does not receive observations of the perturbed scene in this experiment.

## All seven outcomes

| Correction | 80 mm pad-contact trigger | Hold passes | Native placement succeeds |
| --- | --- | --- | --- |
| Unchanged baseline | No | No | Yes |
| X -3 mm | Yes | Yes | Yes |
| X +3 mm | Yes | Yes | Yes |
| Y -3 mm | No | No | No |
| Y +3 mm | No | No | Yes |
| Z -3 mm | Yes | Yes | Yes |
| Z +3 mm | Yes | Yes | Yes |

The four holds retain bilateral-pad contact throughout. Minimum lift ranges from
80.087 to 85.807 mm; maximum object translation ranges from 2.550 to 5.508 mm;
joint range is 0.007963–0.017203 rad. Each advances physics by 1.05 seconds while
holding for 3.215–3.437 wall seconds. These satisfy the original LIBERO bounds:
80 mm minimum lift, 10 mm maximum translation, 0.02 rad joint range, at least
two wall seconds, more than one physics second, and no five-second stall.
This is not a spoken Stop latency measurement. Workbench-specific judges remain
unchanged and were not applied to this different LIBERO placement task.

The independent raw audit recalculates holding metrics, verifies every action
against the source except the one frozen correction, checks all seven outcomes,
and verifies source/actor hashes. The unchanged baseline matches all 103 source
object/joint positions, simulator timestamps, grasp predicates and success
signals exactly. All outcomes are retained, including the negative-Y placement
failure. There are no infrastructure failures or unattempted variants.

Raw files and per-variant rendered videos are local in
`runs/policy-runtime/grasp-alignment-001`; [curated evidence](libero-grasp-alignment-evidence.json)
contains the frozen protocol, all outcomes and raw hashes. Videos use 20fps for
50ms physics steps; they do not reproduce inference or wall-clock timing.
The extracted negative-X holding frame was inspected visually.

```bash
/home/user/.local/share/dume/libero-py38/bin/python scripts/probe_libero_grasp_alignment.py \
  runs/policy-runtime/grasp-alignment-NEW \
  --physics runs/policy-runtime/execution-boundary-010/physics.jsonl \
  --openpi runs/policy-runtime/openpi \
  --config-dir runs/policy-runtime/libero-render-001/config
```

Next: freeze a separate paired fresh-policy experiment before adapting the
controller. Compare unchanged and corrected actions with explicit policy RNG,
fresh observations after interruption, the same physical gates, and new episodes.
Use this known trace for development only. Both signs helping on X/Z while Y
fails argues against treating a world-axis offset as a general recovery rule.
No correction is enabled in any running assistant or promoted policy lab.
