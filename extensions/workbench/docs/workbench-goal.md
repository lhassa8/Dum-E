# Adopted workbench goal — October 11, 2026

User adopted this goal and authorized autonomous implementation. This records the project mandate; current claims are a baseline, not completion evidence.

Build our Dum-E workbench assistant into a highly responsive, useful, expressive simulated robot companion, inspired by the single-arm workshop robot in Iron Man. Own this as a sustained research and development project. Expect substantial work; do not declare the goal achieved after adding a few commands or gestures.

I am a beginner. You are my lead robotics researcher, developer and teacher. Handle implementation, debugging, experiments and technical decisions. Explain important discoveries in plain language and let me learn through working demonstrations. Do not require me to manage individual development steps.

THE EXPERIENCE TO BUILD

I should be able to ask for a tool naturally, receive a prompt response, watch the arm retrieve it, interrupt it, change my mind, resume or return the tool, and have a short conversation with an expressive assistant that understands the current task and workbench.

The assistant should feel attentive and useful. Expression should communicate listening, thinking, acknowledging, acting, success and uncertainty without getting in the way. Avoid long canned speeches, repetitive gestures and unnecessary movement. Never claim that a physical action succeeded without checking its result.

Simulation is the first complete deliverable. Later, we can adapt the system to an SO-101 or another appropriate single arm. Hardware selection and purchases remain separate decisions.

START FROM OUR WORKING PROJECT

Local workspace: /Users/user/Documents/Robot
Fork: https://github.com/lhassa8/Dum-E
Fork checkout: /Users/user/Documents/Robot/Dum-E
Extension: extensions/workbench
Existing feature branch: codex/local-voice-simulation
Current application: http://127.0.0.1:8766/

The current prototype uses MuJoCo Panda physics, an existing local MLX language model, local Whisper transcription and Mac speech output. It delivers screwdriver/wrench/hammer, supports automatic speech completion, spoken Stop, contextual return, resume and bounded expressive movements. Original Dum-E task/MCP interfaces remain in use.

Evidence currently includes 63 passing fork tests, native physical recovery, browser resume/return and saved-speech integration tests. I confirmed live automatic completion and spoken Stop. Live accuracy and latency for other wording remain unmeasured.

Current limitations: scripted manipulation, simulator-state observations rather than camera perception, session-only task context, a single handoff tray, limited speech accepted while busy, and no real robot. The existing language model's size is an implementation choice, not a requirement.

Read the actual code and experiment evidence before changing anything. Relevant documents: /Users/user/Documents/Robot/docs/roadmap.md, /Users/user/Documents/Robot/docs/tool-assistant.md and /Users/user/Documents/Robot/docs/recovery-expression-audit.md. Treat runtime evidence as the baseline; do not confuse planned capabilities with working ones. If this goal is run outside the existing conversation, verify these paths and capabilities first. Execution requires access to the local workspace, command runner, browser and simulator. If those are unavailable, report the access blocker; do not claim local implementation. The lab launch is: uv run --locked --extra assistant --extra dume dume-sim.

Scope comes from my stated workbench-assistant goal, the accepted interactive prototype, and our robotics/world-model roadmap. Camera perception and learned-model work are staged extensions, not claims about the current prototype. Existing skills are preservation requirements; timing objectives below are provisional.

PRIORITIES

1. Responsiveness and dependable interruption.
2. Useful tool handling and coherent interaction.
3. Natural speech and purposeful expression.
4. Perception and recovery from changing conditions.
5. Learning-based improvements that demonstrably help.
6. A clean path to eventual hardware.

Measure where time is spent: end-of-speech detection, recognition, intent selection, planning, speech startup and motion. Common commands should have a fast, bounded path; Stop must never depend on a general language model. Compare smaller models, caching, streaming or other approaches when evidence supports them. Preserve conversational quality and correctness while reducing latency.

Use these provisional responsiveness objectives to guide experiments, not as claims about current performance:
- Visible or audible acknowledgment within 0.5 seconds after the system detects a completed request.
- Common tool requests reach an execution decision within 2 seconds of the user's last spoken word.
- Spoken Stop begins canceling motion within 1 second of the stop utterance ending; measure physical settling separately.
Report median, p95, failures and cold-start behavior. Establish baseline feasibility first, propose justified revisions explicitly, and never quietly redefine timing boundaries or lower a target to obtain a pass.

BUILD IN COHERENT MILESTONES

A. Establish a repeatable interaction and latency benchmark using representative wording, follow-ups, ambiguity, silence, interruptions and background noise. Separate saved-audio tests from live microphone trials.

B. Improve the complete voice-to-action loop. Keep conversation responsive during movement. Handle new requests explicitly instead of silently losing them; make task changes predictable and prioritize Stop. Preserve context across clarification, cancellation and recovery. Keep microphone use visible and controllable. A wake word or idle listening is an optional product/privacy decision, not something to enable silently.

C. Make tool assistance robust when objects change position or a grasp fails. Observe the actual scene, detect failure, recover when a verified recovery exists, and explain uncertainty otherwise. Keep unrelated tools undisturbed. Coordinate gestures with speech and task state; suppress them when they would interfere with a held tool or manipulation.

D. Add camera-based workbench perception and evaluate it against simulator truth before relying on it for motion. Clearly distinguish camera-derived estimates from privileged simulator data. Demonstrate retrieval from varied supported layouts and ask for clarification when identification or localization is uncertain.

E. Improve useful skills with existing robot models, demonstrations, learned dynamics, imitation learning or VLA models where they outperform the simpler baseline. Develop smaller world models as experimental tools for predicting consequences and improving decisions. Do not make training a foundation model a prerequisite for a good assistant.

F. Prepare an interchangeable robot adapter and evaluate candidate hardware requirements. Produce a concrete sim-to-real plan using calibration, sensing, action limits and measured task performance. Do not buy, connect or move real hardware without my explicit authorization.

Choose implementation details and adjust milestone ordering using evidence. Research maintained technologies when making new dependency or model decisions. Prefer modular, replaceable perception, dialogue, task, motion and robot components without building unnecessary infrastructure.

HOW TO WORK

Proceed autonomously with ordinary inspection, edits, tests, experiments and fixes. Do not ask me to approve every feature, implementation choice or milestone. Preserve our existing authorization to publish reviewed changes to this fork's feature branch; do not merge upstream or message other people without authorization.

Ask only when a decision materially changes the goal, requires spending or a paid service, expands microphone/data access, creates an external commitment, or involves destructive changes or real hardware. Prepare a concrete proposal before asking.

Develop on the Apple Silicon Mac where practical. Reinspect capabilities when needed. Use the Windows RTX 5090 workstation later only when available and justified by measured needs. Do not install CUDA-based software on macOS. Favor local processing; do not add paid/cloud dependencies without approval.

Preserve the original world-model experiments and useful Dum-E interfaces. Keep upstream changes traceable. Retain measured placement checks and honest task outcomes; never fake success through teleportation, scripted visual tricks or optimistic language.

For each meaningful change: establish the baseline, state the expected improvement, implement a bounded change, test it, observe the actual result and record what you learned. After two similar failures, investigate the underlying assumption rather than repeat the same attempt. Do not weaken failed checks.

Maintain a concise progress ledger, reusable benchmarks, reproducible dependencies and research notes so work continues across sessions. Keep raw recordings and logs local unless explicitly authorized otherwise. Give brief progress updates and demonstrate completed user journeys, not just code changes.

COMPLETION

This goal is achieved only when the full simulated assistant passes repeatable end-to-end tests for natural requests, useful tool retrieval/return, conversation during work, interruption, task changes, recovery, purposeful expression and camera-informed operation; responsiveness is measured against the explicitly agreed targets; relevant regressions pass; and I have experienced a convincing live demonstration.

Provide a reproducible launch, evidence for each criterion, known limitations and the hardware adaptation plan. Do not represent simulation success as real-hardware readiness. Until then, treat individual milestones as progress and continue with the next useful work rather than repeatedly asking whether to proceed.

Start by assessing the current interaction, measuring latency, identifying the largest bottlenecks, and implementing the first complete improvement.
