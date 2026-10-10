"""Use the enclosing Dum-E checkout, or the lab's pinned source snapshot."""

import sys
from pathlib import Path

VENDOR = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "mcp_server.py").is_file() and (p / "shared/__init__.py").is_file()
    ),
    Path(__file__).parent / "vendor",
)
sys.path.insert(0, str(VENDOR))
