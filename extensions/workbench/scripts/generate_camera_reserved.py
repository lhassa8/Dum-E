"""Freeze a camera candidate first; then generate every prospective case without filtering."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/physical_ai_lab/assistant/camera_control.py",
    "src/physical_ai_lab/assistant/camera_robot.py",
    "src/physical_ai_lab/assistant/perception.py",
    "src/physical_ai_lab/assistant/perception_scene.py",
    "src/physical_ai_lab/assistant/handoff_planning.py",
    "src/physical_ai_lab/assistant/tool_scene.py",
    "src/physical_ai_lab/assistant/tool_geometry.py",
    "src/physical_ai_lab/assistant/scene.py",
    "scripts/verify_camera_delivery.py",
    "scripts/generate_camera_reserved.py",
    "upstream-source.json",
    "uv.lock",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "fixtures/camera_multiview_protocol.json"
    )
    parser.add_argument(
        "--freeze", action="store_true", help="Record source hashes only; generate no cases"
    )
    parser.add_argument(
        "--manifest", type=Path, help="Require a preexisting frozen source manifest"
    )
    args = parser.parse_args()
    hashes = {
        name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in FILES
    }
    protocol_path = args.protocol.resolve()
    hashes[str(protocol_path.relative_to(ROOT))] = hashlib.sha256(
        protocol_path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    runtime = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "mujoco": mujoco.__version__,
    }
    if args.output.exists():
        parser.error("Use a fresh output file")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.freeze:
        args.output.write_text(
            json.dumps(
                {
                    "source_sha256": hashes,
                    "runtime": runtime,
                    "hash_encoding": "LF text; upstream binaries separately verified",
                },
                indent=2,
            )
            + "\n"
        )
        print("Frozen candidate sources; no prospective coordinates generated")
        return
    manifest = {} if args.manifest is None else json.loads(args.manifest.read_text())
    if manifest.get("source_sha256") != hashes or manifest.get("runtime") != runtime:
        parser.error("Candidate/judge/recipe changed or no frozen manifest supplied")
    spec = json.loads(protocol_path.read_text())
    criteria_path = ROOT / "fixtures" / spec["criterion_fixture"]
    if digest(criteria_path) != spec["criterion_fixture_sha256"]:
        parser.error("Protected criterion fixture changed")
    rng = np.random.default_rng(spec["seed"])
    cases = []
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
                "id": f"pc-reserved-{i:03d}",
                "split": "heldout",
                "seed": int(rng.integers(10000000, 20000000)),
                "tool": spec["tools"][i % 3],
                "journey": spec["journeys"][(i // 3) % 3],
                "layout": layout,
                "light": float(rng.uniform(*spec["light_range"])),
            }
        )
    args.output.write_text(
        json.dumps(
            {
                "version": 1,
                "scope": spec["scope"],
                "criteria": json.loads(criteria_path.read_text())["criteria"],
                "cases": cases,
                "protocol_sha256": hashes[str(protocol_path.relative_to(ROOT))],
                "freeze_manifest_sha256": digest(args.manifest),
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"cases": len(cases), "fixture_sha256": digest(args.output)}))


if __name__ == "__main__":
    main()
