"""Bounded, local speech recognition. Recordings are decoded in memory and discarded."""

import asyncio
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

MODEL_REPO = "mlx-community/whisper-small.en-mlx"
MODEL_REVISION = "52a88bf6e98b114a210c21bb83e22d6e1505cb73"
MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 15


def model_path():
    from huggingface_hub import snapshot_download

    return os.environ.get("DUME_SPEECH_MODEL") or snapshot_download(
        MODEL_REPO,
        revision=MODEL_REVISION,
        local_files_only=True,
        allow_patterns=["config.json", "weights.npz"],
    )


def decode_audio(data):
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise ValueError("Record a short request, up to 15 seconds.")
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                "pipe:0",
                "-t",
                str(MAX_SECONDS + 1),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "f32le",
                "pipe:1",
            ],
            input=data,
            capture_output=True,
            timeout=15,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as error:
        raise ValueError("Could not read the recording. Please record again.") from error
    audio = np.frombuffer(result.stdout, dtype=np.float32).copy()
    if not 0.35 * 16000 <= len(audio) <= MAX_SECONDS * 16000:
        raise ValueError("Record a request between one and 15 seconds long.")
    if not np.isfinite(audio).all() or float(np.sqrt(np.mean(audio**2))) < 0.003:
        raise ValueError("I didn't hear speech. Check your microphone and try again.")
    return audio


class SpeechInput:
    def __init__(self):
        self.status = "loading"
        self.error = None
        self.busy = False
        self.path = None
        self.preparation_seconds = None
        self.warmup_seconds = None
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dume-asr")

    def snapshot(self):
        return {
            "status": self.status,
            "error": self.error,
            "busy": self.busy,
            "model": MODEL_REPO,
            "revision": MODEL_REVISION,
            "local": True,
            "preparation_seconds": self.preparation_seconds,
            "warmup_seconds": self.warmup_seconds,
        }

    def _prepare(self):
        started = time.monotonic()
        try:
            if not shutil.which("ffmpeg"):
                raise RuntimeError("Install ffmpeg with: brew install ffmpeg")
            self.path = model_path()
            # Silence skips spoken-word decoding. Exercise the actual path with
            # a bundled synthetic phrase, on the same executor as user requests.
            # No microphone, sound output, conversation or task is involved.
            warmup_started = time.monotonic()
            fixture = Path(__file__).with_name("fixtures") / "recognition-warmup.wav"
            self._recognize(fixture.read_bytes())
            self.warmup_seconds = round(time.monotonic() - warmup_started, 3)
            self.preparation_seconds = round(time.monotonic() - started, 3)
            self.status = "ready"
        except Exception as error:
            self.status = "unavailable"
            self.error = "Voice input unavailable: " + str(error)

    async def prepare(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._prepare)

    def _recognize(self, data):
        import mlx_whisper

        started = time.monotonic()
        audio = decode_audio(data)
        decoded = time.monotonic()
        captured_samples = len(audio)
        # Very short clips can yield no confident segment even with a complete
        # word. Bounded trailing context fixes this without extending capture or
        # weakening speech/confidence gates. Validate the original audio first.
        decoder_padding = 0.35 if captured_samples < 16000 else 0
        if decoder_padding:
            audio = np.pad(audio, (0, int(decoder_padding * 16000)))
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.path,
            language="en",
            temperature=0.0,
            condition_on_previous_text=False,
            verbose=False,
        )
        segments = result.get("segments", [])
        text = " ".join(
            s["text"].strip()
            for s in segments
            if s.get("no_speech_prob", 1) < 0.6 and s.get("avg_logprob", -10) > -1.0
        ).strip()
        if not text:
            raise ValueError("I couldn't make out the words. Please try again.")
        return {
            "text": text[:1500],
            "audio_seconds": captured_samples / 16000,
            "decoder_padding_seconds": decoder_padding,
            "recognition_seconds": round(time.monotonic() - started, 3),
            "audio_decode_seconds": round(decoded - started, 3),
            "model_recognition_seconds": round(time.monotonic() - decoded, 3),
            "model": MODEL_REPO,
            "local": True,
        }

    async def transcribe(self, data):
        with self.lock:
            if self.status != "ready":
                raise RuntimeError(self.error or "Voice input is still loading.")
            if self.busy:
                raise RuntimeError("Another recording is being transcribed.")
            self.busy = True
        future = asyncio.get_running_loop().run_in_executor(self.executor, self._recognize, data)
        # An aborted HTTP client must not permit concurrent model calls.
        future.add_done_callback(lambda _: setattr(self, "busy", False))
        return await asyncio.shield(future)

    def close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
