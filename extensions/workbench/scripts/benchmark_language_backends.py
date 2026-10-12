"""Alternating paired complete responses from Luna and a selected LM Studio model."""

import argparse
import json
import math
import statistics
import time
from dataclasses import asdict
from pathlib import Path

import httpx

from physical_ai_lab.assistant.codex_language import CodexLanguage
from physical_ai_lab.assistant.lmstudio import LMStudioLanguage
from physical_ai_lab.assistant.tool_language import TOOL_SYSTEM, ToolIntent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--lmstudio-model", required=True)
parser.add_argument("--lmstudio-url")
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
    models["codex"] = CodexLanguage(TOOL_SYSTEM, ToolIntent.parse, transport="session")
    models["lmstudio"] = LMStudioLanguage(
        TOOL_SYSTEM, ToolIntent.parse, model=args.lmstudio_model, url=args.lmstudio_url
    )
    startup = {k: m.startup_warmup_ms for k, m in models.items()}
    for repeat in range(args.repeat):
        for index, case in enumerate(cases):
            order = ["codex", "lmstudio"] if (repeat + index) % 2 == 0 else ["lmstudio", "codex"]
            for backend in order:
                row = {"repeat": repeat, "case": case, "backend": backend,
                       "model": str(models[backend].path)}
                began = time.perf_counter()
                try:
                    intent, raw = models[backend].interpret(
                        case["message"], case.get("history", []), observations
                    )
                    row.update(intent=asdict(intent), raw=raw, profile=models[backend].last_profile)
                    row["correct"] = (
                        intent.action in case["actions"] and intent.object == case["object"]
                    )
                except (RuntimeError, ValueError, httpx.HTTPError) as error:
                    row.update(error=str(error), correct=False)
                row["elapsed_ms"] = (time.perf_counter() - began) * 1000
                rows.append(row)
                with (args.output / "rows.jsonl").open("a") as file:
                    file.write(json.dumps(row) + "\n")
                print(f"{backend} {case['name']}: {row['elapsed_ms']:.0f}ms "
                      f"{'correct' if row['correct'] else 'FAIL'}", flush=True)
finally:
    for model in models.values():
        model.close()
    summary = {
        "scope": "Warmed complete text responses, same instructions/schema/requests/context, "
                 "alternating order, no concurrent inference from this benchmark; excludes "
                 "speech, motion, model loading and other-device contention measurement.",
        "startup_warmup_ms": startup, "rows": rows, "results": {},
    }
    for backend in models:
        selected = [r for r in rows if r["backend"] == backend]
        if selected:
            times = sorted(r["elapsed_ms"] for r in selected)
            summary["results"][backend] = {
                "model": str(models[backend].path), "count": len(selected),
                "incorrect": sum(not r["correct"] for r in selected),
                "median_ms": statistics.median(times),
                "p95_ms": times[math.ceil(len(times) * 0.95) - 1],
            }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["results"], indent=2))
