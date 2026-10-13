"""Experimental maintained-Silero edge trim; preserve every interior audio sample."""

import io
import time
import wave

import numpy as np

from physical_ai_lab.dume.asr import decode_audio, trim_speech_edges


def prepare_speech(data):
    started = time.monotonic()
    audio = decode_audio(data)
    decoded = time.monotonic()
    # Retain internal silence, quiet words and possible negation. Never join
    # disjoint voiced islands or remove words inside the first/last interval.
    retained, metadata = trim_speech_edges(audio)
    output = io.BytesIO()
    with wave.open(output, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        file.writeframes((np.clip(retained, -1, 1) * 32767).astype("<i2").tobytes())
    return output.getvalue(), {
        **metadata,
        "decode_ms": (decoded - started) * 1000,
        "prepare_ms": (time.monotonic() - started) * 1000,
    }
