"""Transport safety: positive Stop bypasses blocked GPU; all other speech retains its model."""

import io
import wave
from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.dume.asr import SpeechInput


def audio():
    output = io.BytesIO()
    with wave.open(output, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        samples = .1 * np.sin(2 * np.pi * 440 * np.arange(16000) / 16000)
        file.writeframes((samples * 32767).astype("<i2").tobytes())
    return output.getvalue()


def test_positive_stop_does_not_wait_for_or_call_gpu(monkeypatch):
    monkeypatch.setenv("DUME_ASR_DEVICE", "cuda")
    voice = SpeechInput(edge_trim=False, cpu_stop=True)
    voice.model = SimpleNamespace(transcribe=lambda *a, **k: pytest.fail("GPU was called for Stop"))
    voice.stop_recognizer = SimpleNamespace(inspect=lambda _: {
        "text": "Stop.", "positive_stop": True, "model": "cpu-stop-probe", "revision": "probe",
    })
    try:
        result = voice._recognize(audio(), stop_probe=True)
        assert result["text"] == "Stop." and result["device"] == "cpu"
        assert result["device_fallback"] is False
    finally:
        voice.close()


@pytest.mark.parametrize("incorrect_positive", [False, True])
def test_negation_always_uses_primary_even_if_auxiliary_claims_positive(
    monkeypatch, incorrect_positive
):
    monkeypatch.setenv("DUME_ASR_DEVICE", "cuda")
    voice = SpeechInput(edge_trim=False, cpu_stop=True)
    calls = []

    def primary(*args, **kwargs):
        calls.append(True)
        return [SimpleNamespace(text="Don't stop.", no_speech_prob=0, avg_logprob=0)], None

    voice.model = SimpleNamespace(transcribe=primary)
    voice.stop_recognizer = SimpleNamespace(inspect=lambda _: {
        "text": "Don't stop.", "positive_stop": incorrect_positive,
    })
    try:
        result = voice._recognize(audio(), stop_probe=True)
        assert calls and result["text"] == "Don't stop." and result["device"] == "cuda"
    finally:
        voice.close()


def test_unprepared_configured_cpu_model_cannot_silently_use_gpu():
    voice = SpeechInput(edge_trim=False, cpu_stop=True)
    voice.model = SimpleNamespace(transcribe=lambda *a, **k: pytest.fail("Silent GPU replacement"))
    try:
        with pytest.raises(RuntimeError, match="not ready"):
            voice._recognize(audio(), stop_probe=True)
    finally:
        voice.close()
