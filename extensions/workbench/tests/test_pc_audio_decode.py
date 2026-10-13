"""Real resampling agreement and bounded rejection for the native PC audio path."""

import io
import subprocess
import wave

import numpy as np
import pytest

from physical_ai_lab.dume.asr import decode_audio, ffmpeg_path
from physical_ai_lab.dume.audio_decode import decode_bounded_pcm


def wav(rate, channels, seconds, amplitude=0.2):
    output = io.BytesIO()
    t = np.arange(int(rate * seconds)) / rate
    signals = np.column_stack([amplitude * np.sin(2 * np.pi * (400 + 200 * i) * t)
                               for i in range(channels)])
    with wave.open(output, "wb") as file:
        file.setnchannels(channels)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes((signals * 32767).astype("<i2").tobytes())
    return output.getvalue()


@pytest.mark.parametrize("rate,channels", [(16000, 1), (22050, 1), (44100, 2), (48000, 2)])
def test_real_native_resampling_matches_independent_pcm_reference(rate, channels):
    data = wav(rate, channels, 1.25)
    # The old FFmpeg 7 WAV path mistakes this periodic 48 kHz stereo data for
    # MP3 even with the WAV demuxer. Decode the declared PCM as the independent
    # reference; native must still parse the actual WAV container and resample.
    with wave.open(io.BytesIO(data), "rb") as file:
        raw = file.readframes(file.getnframes())
    reference = subprocess.run([
        ffmpeg_path(), "-nostdin", "-v", "error", "-f", "s16le", "-ar", str(rate),
        "-ac", str(channels), "-i", "pipe:0", "-ac", "1", "-ar", "16000",
        "-f", "f32le", "pipe:1",
    ], input=raw, capture_output=True, timeout=15, check=True)
    native, original = decode_audio(data), np.frombuffer(reference.stdout, dtype=np.float32)
    assert len(native) == len(original) == 20000
    np.testing.assert_allclose(native, original, rtol=0, atol=1e-5)


def test_native_decode_enforces_sample_bound_before_returning_large_audio():
    with pytest.raises(ValueError, match="duration bound"):
        decode_bounded_pcm(wav(16000, 1, 17))


@pytest.mark.parametrize("data", [b"", b"bad container", wav(16000, 1, 0.1),
                                   wav(16000, 1, 1, 0), wav(16000, 1, 16)])
def test_original_speech_duration_and_silence_gates_remain(data):
    with pytest.raises(ValueError):
        decode_audio(data)
