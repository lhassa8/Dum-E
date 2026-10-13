"""Fetch only the immutable local ASR model; runtime never downloads recordings or weights."""

import sys

from huggingface_hub import snapshot_download

from physical_ai_lab.dume.asr import model_identity

if __name__ == "__main__":
    repo, revision = model_identity()
    path = snapshot_download(
        repo,
        revision=revision,
        allow_patterns=["config.json", "weights.npz"] if sys.platform == "darwin" else None,
        token=False,
    )
    print("Local voice model ready:", path)
