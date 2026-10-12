"""Read-only Linux inventory and optional bounded GPU kernel probe. Installs nothing."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

OPENPI_COMMIT = "215abfb217dbac7d5f1273282331b9b1866c0479"

KERNELS = {
    "torch": """
import json, torch
if not torch.cuda.is_available():
    raise RuntimeError('CUDA GPU unavailable; CPU fallback is not a pass')
x = torch.ones((32, 32), device='cuda', dtype=torch.bfloat16)
y = x @ x
torch.cuda.synchronize()
if not torch.isfinite(y).all().item() or not (y == 32).all().item():
    raise RuntimeError('GPU matrix multiplication produced incorrect results')
print(json.dumps({'version': torch.__version__, 'cuda_build': torch.version.cuda,
 'device': torch.cuda.get_device_name(0),
 'capability': list(torch.cuda.get_device_capability(0)),
 'compiled_architectures': torch.cuda.get_arch_list(), 'bfloat16_matmul': True}))
""",
    "jax": """
import json, jax, jax.numpy as jnp
devices = jax.devices('gpu')
if not devices:
    raise RuntimeError('GPU unavailable; CPU fallback is not a pass')
with jax.default_device(devices[0]):
    x = jnp.ones((32, 32), dtype=jnp.bfloat16)
    y = jax.jit(lambda a: a @ a)(x).block_until_ready()
    if not bool(jnp.isfinite(y).all()) or not bool((y == 32).all()):
        raise RuntimeError('GPU matrix multiplication produced incorrect results')
print(json.dumps({'version': jax.__version__, 'device': str(devices[0]),
 'platform': y.device.platform, 'bfloat16_matmul': True}))
""",
}


def run(command, timeout=5, env=None):
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, env=env, check=False
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()[-4000:],
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"returncode": None, "error": str(error)}


def inspect_source(checkout):
    checkout = Path(checkout)
    revision = run(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    with (checkout / "uv.lock").open("rb") as file:
        packages = tomllib.load(file)["package"]
    versions = {
        p["name"]: p["version"]
        for p in packages
        if p["name"] in {"jax", "jaxlib", "jax-cuda12-plugin", "torch"}
    }
    torch = next(p for p in packages if p["name"] == "torch")
    cuda = [
        d["version"]
        for d in torch["dependencies"]
        if d["name"] == "nvidia-cuda-runtime-cu12"
        and "x86_64" in d.get("marker", "")
        and "linux" in d.get("marker", "")
    ]
    return {
        "commit": revision.get("stdout"),
        "matches_pinned_commit": revision.get("stdout") == OPENPI_COMMIT,
        "framework_versions": versions,
        "torch_linux_x86_cuda_runtime": cuda,
        "blackwell_caution": "Inspect CUDA build and run a GPU kernel before model setup. "
        "The pinned Torch CUDA 12.6 build does not establish RTX 5090 support; "
        "JAX compatibility also remains unverified.",
    }


def inventory(engine, checkout=None):
    linux = sys.platform == "linux"
    report = {
        "scope": "Host/runtime preflight; no installs, model weights or robot motion",
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "supported_linux_host": linux,
        "runtime_probe": {"status": "not_requested"},
        "model_ready": False,
        "model_identity_verified": False,
        "closed_loop_demonstrated": False,
    }
    if checkout:
        report["openpi_source"] = inspect_source(checkout)
    if not linux:
        report["runtime_probe"] = {
            "status": "withheld",
            "reason": "The supported LIBERO/OpenPi baseline requires Linux. "
            "No CUDA probe on this host.",
        }
        return report
    report["gpu_inventory"] = (
        run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
        if shutil.which("nvidia-smi")
        else {"error": "nvidia-smi unavailable"}
    )
    if engine != "none":
        env = os.environ.copy()
        env["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
        if engine == "jax":
            env["JAX_PLATFORMS"] = "cuda"
        probe = run([sys.executable, "-c", KERNELS[engine]], timeout=30, env=env)
        passed = probe["returncode"] == 0
        report["runtime_probe"] = {
            "engine": engine,
            "status": "passed" if passed else "failed",
            "process": probe,
        }
        if passed:
            report["runtime_probe"]["result"] = json.loads(probe["stdout"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["none", "jax", "torch"], default="none")
    parser.add_argument("--openpi-checkout", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Use a fresh output path to preserve previous evidence")
    try:
        report = inventory(args.engine, args.openpi_checkout)
    except (OSError, ValueError, KeyError, StopIteration) as error:
        report = {"scope": "Host/runtime preflight", "error": str(error), "model_ready": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report.get("supported_linux_host") or report["runtime_probe"]["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
