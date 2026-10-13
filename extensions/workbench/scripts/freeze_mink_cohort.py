"""Freeze actual runtime/judge/recipe before generating every prospective case."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_manifest(reference_source, recipe_path):
    files = {
        "reference/" + str(p.relative_to(reference_source)): digest(p)
        for p in sorted((reference_source / "physical_ai_lab/assistant").rglob("*"))
        if p.is_file() and (p.suffix == ".py" or "assets" in p.parts)
    }
    for name in (
        "scripts/mink_robot_adapter.py",
        "scripts/benchmark_mink_motion.py",
        "scripts/freeze_mink_cohort.py",
        "fixtures/mink_motion_protocol.json",
        "fixtures/release_model_cases.json",
        "fixtures/camera_multiview_protocol.json",
    ):
        files[name] = digest(ROOT / name)
    files["recipe"] = digest(recipe_path)
    return {
        "files": files,
        "python": sys.version.split()[0],
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("mink", "mujoco", "numpy", "scipy", "qpsolvers", "daqp", "pillow")
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-source", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    manifest = candidate_manifest(args.reference_source, args.recipe)
    if args.output.exists():
        parser.error("Choose a fresh output file")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.freeze:
        result = manifest
    else:
        if args.manifest is None or json.loads(args.manifest.read_text()) != manifest:
            parser.error("Candidate/judge/recipe changed or no frozen manifest supplied")
        spec = json.loads(args.recipe.read_text())
        original = json.loads((ROOT / "fixtures" / spec["source_recipe"]).read_text())
        for name in (
            "case_count",
            "tools",
            "journeys",
            "x_range_m",
            "y_lanes_m",
            "y_jitter_range_m",
            "yaw_range_rad",
            "light_range",
            "criterion_fixture",
            "criterion_fixture_sha256",
        ):
            assert spec[name] == original[name], name
        criterion_path = ROOT / "fixtures" / spec["criterion_fixture"]
        assert digest(criterion_path) == spec["criterion_fixture_sha256"]
        rng, cases = np.random.default_rng(spec["seed"]), []
        for i in range(spec["case_count"]):
            lanes = rng.permutation(spec["y_lanes_m"])
            layout = {
                name: [
                    float(rng.uniform(*spec["x_range_m"])),
                    float(lanes[j] + rng.uniform(*spec["y_jitter_range_m"])),
                    float(rng.uniform(*spec["yaw_range_rad"])),
                ]
                for j, name in enumerate(spec["tools"])
            }
            cases.append(
                {
                    "id": f"mink-prospective-{i:03d}",
                    "split": "heldout",
                    "seed": int(rng.integers(10000000, 20000000)),
                    "tool": spec["tools"][i % 3],
                    "journey": spec["journeys"][(i // 3) % 3],
                    "layout": layout,
                    "light": float(rng.uniform(*spec["light_range"])),
                }
            )
        result = {
            "cases": cases,
            "criteria": json.loads(criterion_path.read_text())["criteria"],
            "hold_frames": spec["hold_frames"],
            "manifest_path": str(args.manifest.resolve()),
            "manifest_sha256": digest(args.manifest),
            "recipe_path": str(args.recipe.resolve()),
            "scope": spec["scope"],
        }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "freeze": args.freeze,
                "sha256": digest(args.output),
                "cases": len(result.get("cases", [])),
            }
        )
    )


if __name__ == "__main__":
    main()
