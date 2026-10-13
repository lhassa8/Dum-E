"""Bounded, local speech recognition. Recordings are decoded in memory and discarded."""

import asyncio
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

MODEL_REPO = "mlx-community/whisper-small.en-mlx"
MODEL_REVISION = "52a88bf6e98b114a210c21bb83e22d6e1505cb73"
FASTER_MODEL_REPO = "Systran/faster-whisper-small.en"
# Set to the immutable upstream revision verified during Windows preparation.
FASTER_MODEL_REVISION = "d1d751a5f8271d482d14ca55d9e2deeebbae577f"
MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 15


def model_identity():
    return (
        (MODEL_REPO, MODEL_REVISION)
        if sys.platform == "darwin"
        else (FASTER_MODEL_REPO, FASTER_MODEL_REVISION)
    )


def ffmpeg_path():
    existing = shutil.which("ffmpeg")
    if existing:
        return existing
    if sys.platform != "darwin":
        from imageio_ffmpeg import get_ffmpeg_exe

        return get_ffmpeg_exe()
    raise RuntimeError("Install ffmpeg before preparing voice input.")


def model_path():
    from huggingface_hub import snapshot_download

    repo, revision = model_identity()
    return os.environ.get("DUME_SPEECH_MODEL") or snapshot_download(
        repo,
        revision=revision,
        local_files_only=True,
        allow_patterns=["config.json", "weights.npz"] if sys.platform == "darwin" else None,
    )


def decode_audio(data):
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise ValueError("Record a short request, up to 15 seconds.")
    try:
        result = subprocess.run(
            [
                ffmpeg_path(),
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


def trim_speech_edges(audio):
    """Keep outer padded speech bounds and every interior sample, including negation."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    options = VadOptions(threshold=0.3, min_speech_duration_ms=120,
                         min_silence_duration_ms=350, speech_pad_ms=400)
    chunks = get_speech_timestamps(audio, options, sampling_rate=16000)
    if not chunks:
        raise ValueError("No supported speech interval; no recognition request sent.")
    first, last = chunks[0]["start"], chunks[-1]["end"]
    return audio[first:last], {
        "original_seconds": len(audio) / 16000, "retained_seconds": (last - first) / 16000,
        "first_sample": first, "last_sample": last, "voiced_intervals": len(chunks),
        "options": {"threshold": 0.3, "min_speech_duration_ms": 120,
                    "min_silence_duration_ms": 350, "speech_pad_ms": 400},
    }


class SpeechInput:
    def __init__(self, edge_trim=False):
        self.status = "loading"
        self.error = None
        self.busy = False
        self.path = None
        self.model = None
        self.edge_trim = edge_trim
        self.device = os.environ.get("DUME_ASR_DEVICE", "cpu")
        self.compute_type = os.environ.get(
            "DUME_ASR_COMPUTE_TYPE", "float16" if self.device == "cuda" else "int8"
        )
        self.preparation_seconds = None
        self.warmup_seconds = None
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dume-asr")

    def snapshot(self):
        return {
            "status": self.status,
            "error": self.error,
            "busy": self.busy,
            "edge_preprocessing": "silero_v6_outer_bounds" if self.edge_trim else "none",
            "model": model_identity()[0],
            "revision": model_identity()[1],
            "backend": "mlx" if sys.platform == "darwin" else "faster-whisper",
            "device": "metal" if sys.platform == "darwin" else self.device,
            "compute_type": self.compute_type if sys.platform != "darwin" else None,
            "local": True,
            "preparation_seconds": self.preparation_seconds,
            "warmup_seconds": self.warmup_seconds,
        }

    def _prepare(self):
        started = time.monotonic()
        try:
            ffmpeg_path()
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
        started = time.monotonic()
        audio = decode_audio(data)
        decoded = time.monotonic()
        captured_samples = len(audio)
        edge_metadata = None
        if self.edge_trim:
            if sys.platform == "darwin":
                raise RuntimeError("Experimental speech edges require the verified PC backend.")
            audio, edge_metadata = trim_speech_edges(audio)
        # Very short clips can yield no confident segment even with a complete
        # word. Bounded trailing context fixes this without extending capture or
        # weakening speech/confidence gates. Validate the original audio first.
        decoder_padding = 0.35 if len(audio) < 16000 else 0
        if decoder_padding:
            audio = np.pad(audio, (0, int(decoder_padding * 16000)))
        prepared = time.monotonic()
        if sys.platform == "darwin":
            import mlx_whisper

            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=self.path,
                language="en",
                temperature=0.0,
                condition_on_previous_text=False,
                verbose=False,
            )
            segments = result.get("segments", [])
        else:
            from faster_whisper import WhisperModel

            if self.device not in {"cpu", "cuda"}:
                raise ValueError("DUME_ASR_DEVICE must be cpu or cuda; no automatic fallback.")
            if self.model is None:
                if self.device == "cuda":
                    import ctranslate2

                    if self.compute_type not in ctranslate2.get_supported_compute_types("cuda"):
                        raise RuntimeError("Requested CUDA compute type unsupported; no fallback.")
                self.model = WhisperModel(
                    self.path,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=8,
                    num_workers=1,
                    local_files_only=True,
                )
                if self.device == "cuda" and self.model.model.device != "cuda":
                    raise RuntimeError("Speech model is not executing on CUDA; no fallback.")
            decoded_segments, _ = self.model.transcribe(
                audio,
                language="en",
                temperature=0.0,
                condition_on_previous_text=False,
                beam_size=1,
                vad_filter=False,
            )
            segments = [
                {"text": s.text, "no_speech_prob": s.no_speech_prob, "avg_logprob": s.avg_logprob}
                for s in decoded_segments
            ]
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
            "speech_preprocessing_seconds": round(prepared - decoded, 3),
            "speech_edge_preprocessing": edge_metadata,
            "model_recognition_seconds": round(time.monotonic() - prepared, 3),
            "model": model_identity()[0],
            "device": "metal" if sys.platform == "darwin" else self.device,
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
