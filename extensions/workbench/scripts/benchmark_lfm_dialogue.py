"""Frozen local dialogue comparison through the actual parser; no robot or microphone calls."""

import argparse
import hashlib
import json
import math
import statistics
import time
from dataclasses import asdict
from pathlib import Path

import httpx

from physical_ai_lab.assistant.lmstudio import LMStudioLanguage
from physical_ai_lab.assistant.tool_language import TOOL_SYSTEM, ToolIntent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--model", required=True)
parser.add_argument("--url", required=True)
parser.add_argument("--native-reasoning", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
args.output.mkdir(parents=True, exist_ok=False)
cases = []
fixture_hashes = {}
for name in ("dialogue_cases.json", "dialogue_context_cases.json", "dialogue_quality_cases.json"):
    path = root / "fixtures" / name
    fixture_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    cases.extend({**c, "name": name.removesuffix(".json")+":"+c["name"]}
                 for c in json.loads(path.read_text()))
encoded = json.dumps(cases, indent=2)+"\n"
fixture_sha = hashlib.sha256(encoded.encode()).hexdigest()
assert len(cases) == 31 and fixture_sha == (
    "aed016fa54905b47478d8181fadd701435dae51fa81a604933bf2ac7dedf4593"
)
(args.output / "merged-fixture.json").write_text(encoded)
protocol = {
    "scope": "Read-only complete intent/reply; excludes speech, motion and camera inference",
    "model": args.model, "unique_cases": 31, "repeats": 3, "planned_cases": 93,
    "fixture_sha256": fixture_sha, "fixture_hashes": fixture_hashes,
    "profile": "native2048" if args.native_reasoning else "existing320-none",
    "temperature": 0, "max_tokens": 2048 if args.native_reasoning else 320,
    "reasoning_effort": "omitted" if args.native_reasoning else "none",
    "json_schema": "Existing strict workbench intent schema",
    "deadline_s": 30, "criterion": "Original allowed action/object plus actual ToolIntent.parse",
    "reply_quality": "Original review descriptions retained for separate qualitative review",
    "actor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "backend_sha256": hashlib.sha256(
        (root / "src/physical_ai_lab/assistant/lmstudio.py").read_bytes()).hexdigest(),
    "parser_sha256": hashlib.sha256(
        (root / "src/physical_ai_lab/assistant/tool_language.py").read_bytes()).hexdigest(),
}
(args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
(args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())


class NativeReasoningTransport(httpx.BaseTransport):
    """Experiment-only payload adapter; production backend/parser remain unchanged."""

    def __init__(self):
        self.inner = httpx.HTTPTransport(trust_env=False)

    def handle_request(self, request):
        if request.url.path == "/v1/chat/completions":
            payload = json.loads(request.content)
            payload.pop("reasoning_effort", None)
            payload["max_tokens"] = 2048
            headers = dict(request.headers)
            headers.pop("content-length", None)
            request = httpx.Request(request.method, request.url, headers=headers, json=payload,
                                    extensions=request.extensions)
        return self.inner.handle_request(request)

    def close(self):
        self.inner.close()


observations = {"positions_m": {}, "locations": {}, "recent_tool": None,
                "interrupted_task": None, "active_task": None, "phase": "Ready"}
rows, model = [], None
report = {"protocol": protocol, "rows": rows}
try:
    model = LMStudioLanguage(
        TOOL_SYSTEM, ToolIntent.parse, model=args.model, url=args.url,
        transport=NativeReasoningTransport() if args.native_reasoning else None,
    )
    report["startup_warmup_ms"] = model.startup_warmup_ms
    for repeat in range(3):
        for case in cases:
            row = {"repeat": repeat, "case": case, "correct": False}
            started = time.perf_counter()
            try:
                intent, raw = model.interpret(
                    case["message"], case.get("history", []), observations)
                row.update(intent=asdict(intent), raw=raw)
                row["correct"] = (
                    intent.action in case["actions"] and intent.object == case["object"])
            except (ValueError, RuntimeError, httpx.HTTPError) as error:
                row["error"] = str(error)
            row.update(elapsed_ms=(time.perf_counter()-started)*1000,
                       profile=model.last_profile)
            rows.append(row)
            with (args.output / "rows.jsonl").open("a") as stream:
                stream.write(json.dumps(row)+"\n")
            print(f"{len(rows)}/93 {case['name']}: {row['elapsed_ms']:.0f}ms "
                  f"{'correct' if row['correct'] else 'FAIL'}", flush=True)
except Exception as error:
    report["startup_error"] = repr(error)
finally:
    if model is not None:
        model.close()
    values = sorted(r["elapsed_ms"] for r in rows)
    report.update(count=len(rows), incorrect=sum(not r["correct"] for r in rows),
                  not_run=93-len(rows))
    if values:
        report.update(median_ms=statistics.median(values),
                      p95_ms=values[math.ceil(.95*len(values))-1], max_ms=max(values))
    (args.output / "summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}), flush=True)
