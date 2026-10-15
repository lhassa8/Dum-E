"""Select by complete physical validation journeys, never training loss."""

import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("state5", type=Path)
parser.add_argument("state6", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
assert not args.output.exists()
heads = ["original", "step50", "step200"]
cases, seen, provenance, identity = [], set(), [], None
for state, directory in ((5, args.state5), (6, args.state6)):
    audit = json.loads((directory/"audit.json").read_text())
    report = json.loads((directory/"report.json").read_text())
    assert audit["audit"] == "pass" and len(report["episodes"]) == 9
    assert not report.get("not_run")
    assert report["protocol"]["batch_initial_state_index"] == state
    assert report["protocol"]["heads"] == heads
    assert report["protocol"]["max_active_steps"] == 220
    current = report["metadata"]["heads"]
    if identity is None:
        identity = current
    assert current == identity
    for result in report["episodes"]:
        key = (state, result["task_id"], result["head"])
        assert key not in seen and result["initial_state_index"] == state
        assert result["error"] is None
        seen.add(key)
        cases.append({"state": state, "task_id": result["task_id"], "head": result["head"],
                      "triggered": result["trigger_reached"], "hold": result["hold_passed"],
                      "fresh_resume": result["fresh_resume_inference"],
                      "released_placement": result["released_placement_passed"],
                      "combined": result["development_passed"]})
    provenance.append({"state": state,
                       "audit_sha256": hashlib.sha256((directory/"audit.json").read_bytes()
                                                       ).hexdigest()})
assert seen == {(state, task, head) for state in (5, 6) for task in (0, 1, 2) for head in heads}
scores = {head: sum(c["combined"] for c in cases if c["head"] == head) for head in heads}
selected = max(heads, key=lambda h: scores[h])  # Stable order implements declared tie break.
output = {"stage": "validation_selection_only", "planned": 18, "cases": cases,
          "scores_out_of6": scores, "selected": selected, "head_identities": identity,
          "tie_break": "Retain original, then earlier training step",
          "candidate_promoted": False, "final_states_7_8_used": False,
          "source_audits": provenance,
          "next": ("Retain original; pilot did not earn replacement. Keep final states unused."
                   if selected == "original" else
                   "Require paired original/selected final evaluation on untouched7/8.")}
args.output.write_text(json.dumps(output, indent=2)+"\n")
print(json.dumps({"scores_out_of6": scores, "selected": selected, "promoted": False}))
