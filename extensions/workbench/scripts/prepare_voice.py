"""Fetch only the immutable local ASR model; runtime never downloads recordings or weights."""

from huggingface_hub import snapshot_download

from physical_ai_lab.dume.asr import MODEL_REPO, MODEL_REVISION

if __name__ == "__main__":
    path = snapshot_download(
        MODEL_REPO,
        revision=MODEL_REVISION,
        allow_patterns=["config.json", "weights.npz"],
        token=False,
    )
    print("Local voice model ready:", path)
