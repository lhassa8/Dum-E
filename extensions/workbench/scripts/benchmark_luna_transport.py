"""Alternating paired subscription calls; both paths use Luna and the same schema."""

import argparse
import json
import math
import statistics
import time
from dataclasses import asdict
from pathlib import Path

from physical_ai_lab.assistant.codex_language import CodexLanguage
from physical_ai_lab.assistant.tool_language import TOOL_SYSTEM, ToolIntent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--repeat", type=int, default=2)
args = parser.parse_args()
if args.repeat < 1:
    parser.error("--repeat must be positive")
args.output.mkdir(parents=True, exist_ok=False)
fixtures = Path(__file__).resolve().parents[1] / "fixtures"
cases = json.loads((fixtures / "dialogue_cases.json").read_text())
cases = [c for c in cases if c["name"] in {"screws", "multiple", "tool_question", "chat"}]
cases += json.loads((fixtures / "dialogue_quality_cases.json").read_text())[:1]
observations = {
    "positions_m": {}, "locations": {}, "recent_tool": None,
    "interrupted_task": None, "active_task": None, "phase": "Ready",
}
models, rows, startup = {}, [], {}
try:
    for transport in ["exec", "session"]:
        models[transport] = CodexLanguage(TOOL_SYSTEM, ToolIntent.parse, transport=transport)
        startup[transport] = models[transport].startup_warmup_ms
    for repeat in range(args.repeat):
        for index, case in enumerate(cases):
            # Alternate order within and between repeats to limit time/order bias.
            order = ["exec", "session"] if (repeat + index) % 2 == 0 else ["session", "exec"]
            for transport in order:
                row = {"repeat": repeat, "case": case, "transport": transport}
                started = time.perf_counter()
                try:
                    intent, raw = models[transport].interpret(
                        case["message"], case.get("history", []), observations
                    )
                    row.update(intent=asdict(intent), raw=raw)
                    row["correct"] = (
                        intent.action in case["actions"] and intent.object == case["object"]
                    )
                    row["profile"] = models[transport].last_profile
                except RuntimeError as error:
                    row.update(error=str(error), correct=False)
                row["elapsed_ms"] = (time.perf_counter() - started) * 1000
                rows.append(row)
                with (args.output / "rows.jsonl").open("a") as file:
                    file.write(json.dumps(row) + "\n")
                print(f"{transport} {case['name']}: {row['elapsed_ms']:.0f}ms "
                      f"{'correct' if row['correct'] else 'FAIL'}", flush=True)
finally:
    for model in models.values():
        model.close()
    summary = {
        "scope": "Warmed full text interpretation, no browser, ASR, speech or motion; "
                 "alternating paired calls, no concurrent inference; cloud jitter remains.",
        "startup_warmup_ms": startup, "rows": rows, "results": {},
    }
    for transport in models:
        selected = [r for r in rows if r["transport"] == transport]
        if selected:
            times = sorted(r["elapsed_ms"] for r in selected)
            summary["results"][transport] = {
                "count": len(selected), "incorrect": sum(not r["correct"] for r in selected),
                "median_ms": statistics.median(times),
                "p95_ms": times[math.ceil(len(times) * 0.95) - 1],
            }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["results"], indent=2))
