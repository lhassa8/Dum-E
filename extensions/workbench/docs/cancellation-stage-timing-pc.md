# Separating cancellation from queue cleanup — PC

The preceding complete voice qualification passed all six physical/state
journeys, but one native-cancellation deadline remained unproven: its conservative
interval was 925.60–1012.40 ms. That original result remains unchanged.

The Stop endpoint first awaits the native cancellation acknowledgment, then
cancels outstanding original Dum-E tasks. The final HTTP reply therefore includes
time spent on queue cleanup after cancellation is already confirmed.

The bridge now records monotonic timestamps immediately before Stop, after the
native acknowledgment, and after queue cleanup. The endpoint returns the same
cancellation ID and intervals stored in local `cancellation-timing.jsonl`.
The verifier matches that ID, checks the exact timestamp-derived duration and
ordering, and rejects telemetry longer than the browser round trip.

For a word-end reference W, native cancellation S, native acknowledgment A,
cleanup completion C and browser reply E, S <= A <= C <= E. Thus
`E - W - (C - A)` still bounds `S - W` from above. The implementation rounds
the subtracted interval down to whole milliseconds, preserving a conservative
bound. It does not subtract recognition, request transport, or time before
native acknowledgment. Browser and WSL wall clocks are never subtracted.

The protected objective is still cancellation beginning within 1000 ms of the
saved word-end reference. Settling/holding remains a separate test. Logging is
after the physical Stop signal and does not postpone it. A contract test verifies
native cancellation precedes all task cancellations, every pending/running task
is cancelled, and the returned record equals the local log.

The same six full natural-voice journeys are frozen again before inference.
The new measurement does not retroactively change or promote the earlier run.
Full acoustic timing, acknowledgment, echo and human-controlled microphone
validation remain part of the sustained goal.

Run008 ended after two complete journeys: a camera response failed the existing
model-identity check and surfaced as a409 dialogue error before Stop could
supersede it. The Stop transcript and native cancellation event are nevertheless
present. The loaded-model inventory showed only Bonsai; the selected Gemma
instance was absent. The reason it became unloaded is unknown.

The camera logs also exposed a qualification gap in run007: its six camera
requests include two timeouts and four identity rejections. Keep its physical
and state results, but withdraw the claim that it qualified interruption under
the intended Gemma workload. The independent judge now rejects these camera
workload failures, including failed requests later superseded by Stop.

Reloaded the already-local Gemma4 31B Q4_K_M as `workbench-vision-gemma`, full
GPU offload,4096context,oneprediction slot,3600second idleTTL. A real camera
response verified its exact identity before retry009. Bonsai's observed current
configuration is8192context,fourprediction slots; that configuration was
preserved. Before-run inventory is retained locally with the frozen six cases.

Retry009 independently passes all six complete journeys, including six verified
pending camera replies superseded by Stop, twelve placements, completion-aware
Proceed without pickup, and contextual returns. Conservative cancellation
bounds:861.00ms median,979.70ms samplep95/max,n=6. Confirmed cleanup subtractions
rounded down:0/0/2/1/1/1ms. The uncorrected bounds also pass,861.50/980.70ms;
this run's pass is not attributable to subtracting queue cleanup. Variability
and the changed loaded-model state prevent a causal speedup claim.

Minimum lift201.33mm,maximum placementerror9.24mm,settledjointdrift0.001438rad,
heldtranslation0.520mm,observerage135.0ms. No camera workload errors in these
six jobs. Source/PCM identities and all original criteria pass. ProtocolSHA:
`b3bd58dd3d97bf68c7f8259e6aa2f492e0c888da0ca8424593e586c63a32e6a1`.
Raw evidence:`runs/pc-physical-voice-stop-009`,native:`runs/dume-8619c0ac`.

Seven retained-record checks pass: original verdict retained; altered identity,
inflated cleanup,reordered timestamps,lateStop,completedProceed pickup,and wrong
camera workload rejected. Full Python suite344passes in229.31s with one existing
dependency warning; browser capture/VAD contracts and Ruff pass; all46 upstream
files remain unchanged. This is a small saved-SAPI-voice qualification, with
prewarmed recognizers and concurrently loaded local models. It does not qualify
live acoustic latency, acknowledgment,echo,broader layouts or realhardware.
