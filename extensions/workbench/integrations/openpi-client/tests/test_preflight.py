"""Preflight contract checks; these do not emulate or certify an NVIDIA GPU."""

import importlib.util
import sys
from pathlib import Path

import pytest

script = Path(__file__).parents[1] / "scripts/workstation_preflight.py"
spec = importlib.util.spec_from_file_location("preflight", script)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def test_non_linux_host_withholds_even_explicit_gpu_probe(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")

    def unexpected_command(*args, **kwargs):
        pytest.fail("GPU/runtime commands must not execute on Mac")

    monkeypatch.setattr(preflight, "run", unexpected_command)
    report = preflight.inventory("jax")
    assert report["runtime_probe"]["status"] == "withheld"
    assert report["model_ready"] is False and report["closed_loop_demonstrated"] is False


def test_no_runtime_probe_does_not_imply_gpu_or_model_readiness(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
    report = preflight.inventory("none")
    assert report["supported_linux_host"] is True
    assert report["runtime_probe"]["status"] == "not_requested"
    assert report["model_ready"] is False
