"""Inference-only loading of pinned OpenVLA-OFT modules, without training imports."""

import ast
import hashlib
import math
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SOURCE_COMMIT = "e4287e94541f459edc4feabc4e181f537cd569a8"


def load_helpers(source):
    source = Path(source).resolve()
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"],
                                   text=True).strip() == SOURCE_COMMIT
    sys.path.insert(0, str(source))
    # These __init__ files import full training/data stacks. Inference uses the
    # original modules below, not those unrelated package-level exports.
    for name, directory in (("prismatic", "prismatic"),
                             ("prismatic.models", "prismatic/models"),
                             ("prismatic.training", "prismatic/training"),
                             ("prismatic.vla", "prismatic/vla")):
        assert name not in sys.modules, "Use a fresh isolated inference process"
        package = types.ModuleType(name)
        package.__path__ = [str(source/directory)]
        sys.modules[name] = package
    path = source/"experiments/robot/openvla_utils.py"
    module = ast.parse(path.read_text())
    replaced = 0
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module == (
                "prismatic.vla.datasets.rlds.utils.data_utils"):
            assert [alias.name for alias in node.names] == ["NormalizationType"]
            node.module = "prismatic.vla.constants"
            replaced += 1
    assert replaced == 1
    data_source = ast.parse((source/"prismatic/vla/datasets/rlds/utils/data_utils.py").read_text())
    assert any(isinstance(n, ast.ImportFrom) and n.module == "prismatic.vla.constants"
               and any(a.name == "NormalizationType" for a in n.names) for n in data_source.body)
    helpers = types.ModuleType("experiments.robot.openvla_utils")
    helpers.__file__ = str(path)
    exec(compile(module, str(path), "exec"), helpers.__dict__)
    # All components are already local. Avoid optional Hub discovery calls.
    helpers.model_is_on_hf_hub = lambda _: False
    sys.modules[helpers.__name__] = helpers
    geometry_path = source/"experiments/robot/libero/libero_utils.py"
    names = {"get_libero_image", "get_libero_wrist_image", "quat2axisangle"}
    definitions = [n for n in ast.parse(geometry_path.read_text()).body
                   if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(definitions) == 3
    geometry = {"np": np, "math": math}
    geometry_module = ast.Module(body=definitions, type_ignores=[])
    exec(compile(geometry_module, str(geometry_path), "exec"), geometry)
    return helpers, geometry, {
        "source_commit": SOURCE_COMMIT,
        "helpers_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "geometry_sha256": hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
        "compatibility": "Training exports skipped; identical normalization enum imported directly",
    }


def configuration(checkpoint):
    return SimpleNamespace(pretrained_checkpoint=str(Path(checkpoint).resolve()),
                           use_l1_regression=True, use_diffusion=False, use_film=False,
                           num_images_in_input=2, use_proprio=True, center_crop=True,
                           unnorm_key="libero_spatial_no_noops", load_in_8bit=False,
                           load_in_4bit=False)


def observation(raw, geometry):
    return {
        "full_image": np.ascontiguousarray(geometry["get_libero_image"](raw)),
        "wrist_image": np.ascontiguousarray(geometry["get_libero_wrist_image"](raw)),
        "state": np.concatenate((raw["robot0_eef_pos"],
                                 geometry["quat2axisangle"](raw["robot0_eef_quat"].copy()),
                                 raw["robot0_gripper_qpos"])),
    }


def native_actions(actions):
    """Publisher LIBERO conversion: seven OSC inputs, never Panda joint targets."""
    actions = np.asarray(actions).copy()
    assert actions.shape == (8, 7) and np.isfinite(actions).all()
    actions[:, -1] = -np.sign(2*actions[:, -1]-1)
    return actions
