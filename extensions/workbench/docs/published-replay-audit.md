# Published action replay: five of six physical passes

The frozen six-case replay completes every case. All six reach native task
success and a bilateral-pad grasp/lift trigger; five also satisfy released,
resting placement. Exact recorded-state fidelity passes zero of six. Keep
these claims separate: this executes recorded human actions in native physics,
not fresh model inference, a trained adaptation or a complete interrupted journey.

The [prospective protocol](published-replay-protocol.json) selects demo0/1 in
tasks0/1/2 before replay outcomes. The verified publisher files and prior
scene-identity inspection are described in the
[corpus inspection](published-demonstration-inspection.md). No selected case is
flagged by that conservative near-duplicate rule; this is not a claim of novelty
relative to the checkpoint's original training data.

## Initialization, action and physical evidence

Each case loads the episode XML, relocating93asset-file paths into existing
local asset roots. The first recorded state initializes simulation; there are
no dummy actions. Geometry/actuator parameters are not edited. Native OSC uses
kp150 and original input/output scaling. All683source actions exactly match
the HDF5 values;21zero-OSC settling actions per episode preserve its final
gripper command. No release is invented for a closed final command. All809
active actions fit the unchanged220step per-episode budget.

Attempt001 uses a Python3.9-only path API in the Python3.8 simulator and fails
before any action in all six cases. It is preserved. Replacing only that path
containment check permits fresh attempt002; no task/action/threshold is changed.

| Task/demo | Active steps | Bilateral80mm lift trigger | Native goal | Released placement | XY error |
|---|---:|---|---|---|---:|
|0/0|119|Yes|Yes|Pass|8.400mm|
|0/1|105|Yes|Yes|Pass|9.550mm|
|1/0|173|Yes|Yes|Pass|8.918mm|
|1/1|144|Yes|Yes|Pass|7.078mm|
|2/0|124|Yes|Yes|Fail: gripper still contacts bowl|14.006mm|
|2/1|144|Yes|Yes|Pass|15.875mm|

Released placement requires native success, actual plate contact and zero
gripper/object contact throughout the final0.5sim seconds,≤35mm XY error and
≤5mm object movement. The failed case moves only0.313mm and reaches the goal,
but still fails the protected contact requirement. No optimistic success label
substitutes for release. The lift trigger alone does not prove stable holding;
original joint Stop/hold/resume remains untested for these demonstrations.

Independent auditing recomputes dense2ms contact/lift/release/movement gates,
matches every applied source action against the HDF5, and checks the settling
commands. Three altered raw witnesses—gripper contact, missing plate support,
or native goal failure—are each rejected. Actual pre-action front/wrist256RGB
observations plus terminal frames produce local20Hz simulation videos. Terminal
renders for task1/demo0 and failed task2/demo0 were visually inspected. Videos
show recorded human-action replay, exclude wall-clock loading/stalls, and have
no microphone/audio component.

## State fidelity and observation alignment

All six exceed the prospective1e-6full-state error threshold. A separate first-case
diagnostic retains full replay states and reproduces the same physical outcome
and maximum reference discrepancy2.636296. The initial state error is exactly0;
the worst later discrepancy is at step80 in a plate velocity component. Maximum
Panda joint-position difference is8.577mrad. The flattened state contains mixed
position/velocity components; its maximum error is not a distance in meters.
The cause of later dynamic divergence is not established. Do not relax fidelity
or present the replay as an exact reproduction of recorded states.

Across the six cases, median EEF errors against stored observation[j] are
7.929–11.395mm before action[j], versus0.319–0.543mm after it. This supports the
post-action observation alignment found in conversion source. Dynamic divergence
prevents claiming exact sensor alignment. Do not feed stored image[j] to learn
unverified action[j] pairs. Actual native pre-action observations are retained
separately and could support newly collected supervision after qualification.

Raw data/videos remain in `runs/grasp-adaptation/published-replay-002/`, with
the one-case diagnostic in `published-fidelity-diagnosis-001/`. Only
[aggregate evidence](published-replay-evidence.json) is published. No model
weights or public assistant control paths change. Next test interrupted holding
on the same prospective cases, retain the failed release, and then construct
state-separated adaptation data from independently qualified observations/actions.
