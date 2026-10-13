"""Frozen read-only task-selection comparison; never actuates or records audio."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import statistics
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--prepare-fixture", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "fixtures/decider_task_selection_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    cases, fixture_hashes = [], {}
    for name in protocol["fixtures"]:
        path = root / "fixtures" / name
        fixture_hashes[name] = sha(path)
        for case in json.loads(path.read_text()):
            cases.append({**case, "name": name.removesuffix(".json") + ":" + case["name"]})
    args.output.mkdir(parents=True, exist_ok=True)
    merged = args.output / "merged-fixture.json"
    encoded = json.dumps(cases, indent=2) + "\n"
    if merged.exists() and merged.read_text() != encoded:
        raise ValueError("Frozen fixture changed")
    merged.write_text(encoded)
    if args.prepare_fixture:
        print(
            json.dumps(
                {
                    "count": len(cases),
                    "fixture_sha256": sha(merged),
                    "protocol_sha256": sha(protocol_path),
                }
            )
        )
        return
    if args.checkpoint is None:
        parser.error("--checkpoint is required for inference")
    result_files = ("decider-summary.json", "decider-rows.jsonl")
    if any((args.output / name).exists() for name in result_files):
        raise ValueError("Refusing to overwrite an existing run; choose a new output directory")

    import torch
    from strands_decider.infer import load_engine
    from strands_decider.schema import ChoiceQuestion

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; no CPU fallback")
    # A visible GPU is insufficient: execute actual bf16 matmul and synchronize.
    x = torch.ones((64, 64), dtype=torch.bfloat16, device="cuda")
    actual = (x @ x).float().sum().item()
    assert actual == 64 * 64 * 64
    torch.cuda.synchronize()
    del x
    report = {
        "scope": "task selection only; excludes speech, replies and motion",
        "protocol_sha256": sha(protocol_path),
        "fixture_sha256": sha(merged),
        "source_fixtures": fixture_hashes,
        "checkpoint": str(args.checkpoint),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "peft", "strands-decider")
        },
        "gpu": torch.cuda.get_device_name(),
        "cuda": torch.version.cuda,
        "capability": torch.cuda.get_device_capability(),
        "compiled_arches": torch.cuda.get_arch_list(),
        "bf16_matmul_result": actual,
        "prefix_cache": False,
        "rows": [],
    }
    question = ChoiceQuestion(instructions=protocol["instruction"], criteria=protocol["options"])
    try:
        started = time.perf_counter()
        engine = load_engine(str(args.checkpoint), device="cuda", use_prefix_cache=False)
        torch.cuda.synchronize()
        report["load_ms"] = (time.perf_counter() - started) * 1000
        report["parameter_devices"] = sorted({str(p.device) for p in engine.model.parameters()})
        assert all(p.device.type == "cuda" for p in engine.model.parameters())
        for repeat in range(protocol["repeats"]):
            for case in cases:
                state = {
                    "current_user_message": case["message"],
                    "conversation_history": case.get("history", []),
                }
                torch.cuda.synchronize()
                started = time.perf_counter()
                result = engine.ask(state, {"intent": question})
                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - started) * 1000
                answer = result.answers["intent"]
                label = answer.choice
                if label.startswith(("fetch_", "return_")):
                    action, obj = label.split("_", 1)
                else:
                    action, obj = label, None
                correct = action in case["actions"] and obj == case["object"]
                row = {
                    "repeat": repeat,
                    "name": case["name"],
                    "elapsed_ms": elapsed,
                    "correct": correct,
                    "action": action,
                    "object": obj,
                    "response": result.model_dump(),
                }
                report["rows"].append(row)
                with (args.output / "decider-rows.jsonl").open("a") as file:
                    file.write(json.dumps(row) + "\n")
                print(
                    f"{len(report['rows'])}: {case['name']} {elapsed:.1f}ms "
                    f"{'correct' if correct else 'FAIL'} conf={answer.confidence:.3f}",
                    flush=True,
                )
        rows = report["rows"]
        warm = sorted(row["elapsed_ms"] for row in rows[1:])
        report.update(
            count=len(rows),
            incorrect=sum(not r["correct"] for r in rows),
            first_request_ms=rows[0]["elapsed_ms"],
            warm_count=len(warm),
            warm_median_ms=statistics.median(warm),
            warm_p95_ms=warm[math.ceil(0.95 * len(warm)) - 1],
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
        )
        report["high_confidence_errors"] = sum(
            not r["correct"]
            and r["response"]["answers"]["intent"]["confidence"] >= protocol["confidence_threshold"]
            for r in rows
        )
    except Exception as exc:
        report["error"] = repr(exc)
        raise
    finally:
        (args.output / "decider-summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
