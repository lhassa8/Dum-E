# Published LIBERO demonstrations verified locally

The three relevant publisher HDF5 files are downloaded and independently
rehashed against pinned LFS identities:1,769,993,928bytes total,150episodes.
These are existing human demonstrations, not new learned-policy rollouts.
No demonstration action has been applied and no weights have been trained.

The [official LIBERO downloader](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/libero/libero/utils/download_utils.py)
references [yifengzhu-hf/LIBERO-datasets](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets).
Revisionf13aa24a3da8c43c7225569f28c562979fa0e35a is pinned, with Apache2.0
dataset-card metadata. Only the three task files are acquired. The bounded
downloader checks every HTTP range, preserves partial transfers, and verifies
complete file lengths/SHA256. Files remain under
`runs/grasp-adaptation/official-demonstrations-001/`; only aggregates are published.

## Actual structure

| Task | Episodes | Raw action steps min/median/max | Within220raw steps |
|---|---:|---:|---:|
|0: bowl between plate/ramekin|50|75/95/168|50|
|1: bowl next to ramekin|50|109/132.5/189|50|
|2: bowl at table center|50|93/117/164|50|

Every recorded action is finite, seven-dimensional, and within the native±1
input range. Stored front/wrist images are128×128RGB; proprioception includes
EEF position/axis-angle, two gripper joints and seven arm joints. All150episode
XML joint-name orders match the installed task-model topology. That establishes
state-array indexing compatibility, not identical dynamics or replay accuracy.
The inspector constructs/resets native models for topology; it applies no actions.

These episode lengths are promising compared with the geometric teacher's
211–214steps on task0. They do not prove completion under our budget: extra
settling, interruption and physical release checks remain to be executed.

## Identity and timing caveats

The initial full-state comparison finds no exact layout match, but a shared
approximately72mm offset dominates it. The initial cabinet-hinge explanation
was premature; free-object vertical differences also dominate the metric.
Inspection003 compares full3D free-object position and orientation. Final
inspection004 conservatively compares tabletopXY and quaternion orientation,
so vertical settling cannot itself establish a different scene. Failed NumPy
indexing attempt002 and the earlier inspections remain local and are not used
to clear training data.

The fixed near-duplicate exclusion rule requires every movable free object's
XY distance≤10mm and orientation distance≤50mrad to a benchmark state; overlap
with state0/5/6/7/8 excludes an episode. No episode meets this complete overlap
rule. That is a narrowly scoped fingerprint result, not proof of broad visual
novelty or independence from the pretrained checkpoint's original training data.
No one-to-one correspondence between demonstration numbers and benchmark initial
state numbers is established. A prospective demonstration-level training selection
and independent physical evaluation split remain necessary before adaptation.

The pinned `scripts/create_dataset.py` conversion steps action[j], records the
resulting images/proprioception, then retains states[j] and actions[j]. Its first
five steps are omitted. Thus treating stored image[j] as an unverified pre-action
input risks a timing offset. Next compare native replay states and observed
proprioception against both candidate alignments. Re-render actual pre-action
observations if required. Do not silently relabel shifted pairs as correct.

## Next physical experiment

Freeze a bounded human-demonstration replay set across all three tasks, retain
all outcomes, and reproduce native state/action semantics from the episode XML.
First establish unpaused replay fidelity, real pad contacts/lift and released
placement; then test original joint holding at a qualified lift. Published
success flags alone do not qualify Stop/hold/resume or a secure grasp. Model
selection/final benchmark states remain separate. The dependable public assistant
is unchanged.

Full file identities and aggregate structure are in
[the evidence](published-demonstration-evidence.json). No raw HDF5, observations,
XML, trajectories or recordings are committed.
