"""Execute real BF16 policy-family kernels on the RTX GPU; no checkpoint or simulation."""

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn.functional as functional

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
assert torch.cuda.is_available(), "CUDA required; no CPU fallback"
device = torch.device("cuda:0")
capability = torch.cuda.get_device_capability(device)
assert capability == (12, 0), "This preflight is for the configured RTX5090"
torch.manual_seed(7)
results = []
for name in ("matmul", "convolution", "layer_norm", "attention"):
    if name == "matmul":
        a, b = [torch.randint(-2, 3, (64, 64), dtype=torch.float32) for _ in range(2)]
        expected = a @ b
        def operation():
            return a.to(device, dtype=torch.bfloat16) @ b.to(device, dtype=torch.bfloat16)
    elif name == "convolution":
        a = torch.randint(-2, 3, (1, 3, 32, 32), dtype=torch.float32)
        b = torch.randint(-2, 3, (8, 3, 3, 3), dtype=torch.float32)
        expected = functional.conv2d(a, b)
        def operation():
            return functional.conv2d(a.to(device, dtype=torch.bfloat16),
                                     b.to(device, dtype=torch.bfloat16))
    elif name == "layer_norm":
        a = torch.randint(-2, 3, (4, 64), dtype=torch.float32)
        expected = functional.layer_norm(a, (64,))
        def operation():
            return functional.layer_norm(a.to(device, dtype=torch.bfloat16), (64,))
    else:
        a, b, c = [torch.randint(-2, 3, (1, 4, 32, 64), dtype=torch.float32) for _ in range(3)]
        expected = functional.scaled_dot_product_attention(a, b, c, is_causal=False)
        def operation():
            return functional.scaled_dot_product_attention(
                a.to(device, dtype=torch.bfloat16), b.to(device, dtype=torch.bfloat16),
                c.to(device, dtype=torch.bfloat16), is_causal=False)
    torch.cuda.synchronize()
    started = time.monotonic()
    actual = operation()
    torch.cuda.synchronize()
    elapsed = (time.monotonic()-started)*1000
    assert actual.device.type == "cuda" and torch.isfinite(actual).all()
    error = float((actual.cpu().float()-expected).abs().max())
    tolerance = .02 if name in ("layer_norm", "attention") else 0
    assert error <= tolerance, (name, error, tolerance)
    results.append({"kernel": name, "dtype": str(actual.dtype), "device": str(actual.device),
                    "max_absolute_error": error, "tolerance": tolerance,
                    "first_call_including_transfer_ms": elapsed})
report = {"passed": True, "torch": torch.__version__, "cuda_build": torch.version.cuda,
          "gpu": torch.cuda.get_device_name(device), "capability": capability,
          "compiled_architectures": torch.cuda.get_arch_list(), "kernels": results,
          "scope": "Real GPU preflight; does not prove policy inference or performance"}
(args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report))
