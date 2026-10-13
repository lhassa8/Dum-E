# Odyssey-3 assessment for the workbench arm

Assessment date: October 13, 2026. Odyssey-3 merits a focused recovery-policy
research track. Arm integration depends on access to its robotics representation
and action-decoder interface; the public video preview alone cannot establish
that integration. Keep the measured local controller and independent physics
judges while evaluating this opportunity.

## Relevant capabilities

Odyssey describes an autoregressive diffusion-transformer world model. A learned
action decoder adapts its representations to a machine using paired observations
and actions. Its reported arm experiments use tens of hours of demonstrations
and show recovery from missed grasps and unusually positioned dropped objects.
Those are company-reported demonstrations, without a reproducible Dum-E success
rate in the announcement. [Robotics introduction](https://odyssey.systems/introducing-odyssey-3).

The October 8 launch provides a research preview of generated interactive
environments and invites physical-AI developers to contact the company. The
launch also reports physical-video and world-generation benchmarks. These measure
generated-world properties, rather than our contact retention, placement or
Stop/resume requirements. [Launch](https://odyssey.systems/meet-odyssey-3),
[benchmark scope](https://physics-iq-verified.anates.ai/).

## Access and workstation fit

The official public documentation index still names Odyssey-2 Pro. The public
Python SDK supports image-conditioned streams, text interaction and scripted
video generation. Neither establishes an Odyssey-3 numerical robot-action
endpoint. [Documentation](https://documentation.api.odyssey.ml/llms.txt),
[official SDK](https://github.com/odysseyml/odyssey-python).

Odyssey's public Hugging Face model list currently contains three CUDA kernel
packages, without an Odyssey-3 checkpoint. The reviewed public material does not
provide a supported 32GB RTX 5090 inference or fine-tuning recipe. Local weights,
model size, robot-policy access and deployment cost remain practical access
questions. A client SDK being open source does not make the foundation weights
open. [Model hub](https://huggingface.co/odyssey-systems/models).

Existing API terms include use of customer prompts and outputs for model
development and training; the definitions still reference Odyssey-2. Confirm
the applicable Odyssey-3 arrangement before sharing project data. No account,
paid request, upload or vendor message is authorized by this assessment.
[Current API terms](https://odyssey.systems/legal/api-terms).

## Proposed role in our system

My strongest hypothesis is a pretrained visual representation plus an arm-specific
action decoder for recovery. Our current rigid held-pose estimate can drift while
the binary grip proxy remains satisfied. Odyssey's reported recovery behaviors
make this a relevant hypothesis to test, without assuming it can identify our
tool contacts or grip forces from images.

An accessible image-conditioned generator could also produce appearance and
lighting variations for perception research. Such images would carry synthetic
provenance and would not supply authoritative physical labels. Existing exhausted
held-pose and release-model fit budgets remain exhausted; this is a distinct
future research proposal, not permission to repeat those fits.

Predicting consequences of candidate arm actions could eventually support
planning, but only with a documented action-conditioned interface, calibrated
observations and measured latency. Text describing a gripper movement is not
equivalent to conditioning on our actual joint or end-effector command.

## Concrete evaluation sequence

1. Resolve robotics access: supported arms and cameras, decoder training interface,
   proprioception inputs, action units/frame/rate, checkpoint or hosted deployment,
   RTX 5090 requirements, pricing and data handling. Obtain a reproducible model
   identifier and version before implementing an adapter.
2. With separately authorized access, benchmark offline predictions or a decoder
   using camera observations and robot proprioception. Keep evaluator-only object
   state out of policy inputs. Separate demonstration, validation and test scenes.
   Measure multi-step physical error, grasp-loss prediction precision/recall,
   uncertainty and inference median/p95. Benchmark against our measured local
   controller and actual OpenPi policy in their supported embodiments.
3. Execute proposals only through the existing bounded robot port in MuJoCo.
   Preserve tool_contacts_v2, gravity hold, stale-action rejection and independent
   Stop. Count complete retrieval, delivery, return, interruption and task-change
   journeys, including refusals and failed recoveries. Retain 80mm lift, 35mm
   placement, resting/open-hand and unrelated-tool checks. Generated video cannot
   be the success judge. Freeze before a prospective cohort; require the existing
   95% full-journey gate and full latency/human-demo criteria before promotion.

## Questions prepared for Odyssey

- Is robotics access to Odyssey-3 available to independent developers, and how
  does it differ from the Flash interactive preview and public video API?
- Can we adapt a Panda in MuJoCo first, then a chosen workbench arm, using our own
  synchronized camera/proprioception/action demonstrations? Is simulation data supported?
- What are the output action space, control frequency, inference latency and
  mechanisms for cancellation, stale observations and uncertainty?
- Are frozen representations or decoder-training checkpoints available locally?
  What VRAM/runtime is required, and is sm120 supported?
- What are the applicable fees, retention/training terms, version guarantees and
  published quantitative robotics evaluations?

These questions are prepared locally; no message has been sent. At the time of
this assessment, published local baseline was1c77eab and gap recovery was unpromoted:
first retrospective replay50/54 versus published51/54, with two conservative
tabletop-grasp refusals. Preserve its failed traces while continuing research;
do not use it as evidence that the arm is already qualified.
