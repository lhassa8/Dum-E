"""Bounded local SAPI synthesis through a persistent Windows PowerShell worker."""

import base64
import io
import json
import queue
import subprocess
import threading
import uuid
import wave
from pathlib import Path


class WindowsSpeech:
    def __init__(self):
        self.process = None
        self.responses = queue.Queue()
        self.lock = threading.Lock()
        self.voice = None

    def _receive(self, timeout):
        try:
            response = self.responses.get(timeout=timeout)
        except queue.Empty as error:
            raise RuntimeError("Windows speech worker exceeded its response deadline.") from error
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise RuntimeError("Windows speech worker exited.")
        return response

    def prepare(self):
        root = Path(__file__).resolve().parents[3]
        script = subprocess.check_output(
            ["wslpath", "-w", str(root / "scripts/windows_speech_worker.ps1")],
            text=True, timeout=5,
        ).strip()
        self.process = subprocess.Popen([
            "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            "-NoProfile", "-File", script,
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8")

        def read():
            try:
                while line := self.process.stdout.readline(3_000_001):
                    if len(line) > 3_000_000 or not line.endswith("\n"):
                        raise RuntimeError("Oversized Windows speech response.")
                    self.responses.put(json.loads(line))
            except Exception as error:
                self.responses.put(error)
            finally:
                self.responses.put(None)

        threading.Thread(target=read, daemon=True).start()
        ready = self._receive(5)
        if ready.get("kind") != "ready" or ready.get("local") is not True:
            raise RuntimeError("Windows speech did not report a local installed voice.")
        self.voice = ready["voice"]
        self.synthesize("Let me check.")

    def synthesize(self, text):
        if not isinstance(text, str) or not 1 <= len(text) <= 500:
            raise ValueError("Speech requires 1–500 characters.")
        if not self.process or self.process.poll() is not None or not self.voice:
            raise RuntimeError("Windows speech worker is unavailable.")
        if not self.lock.acquire(timeout=2):
            raise RuntimeError("Windows speech worker is busy.")
        try:
            identity = uuid.uuid4().hex
            self.process.stdin.write(json.dumps({"id": identity, "text": text}) + "\n")
            self.process.stdin.flush()
            result = self._receive(12)
            if result.get("id") != identity or result.get("kind") != "audio":
                raise RuntimeError(result.get("error", "Windows speech identity mismatch."))
            if result.get("local") is not True or result.get("voice") != self.voice:
                raise RuntimeError("Unexpected speech provider or voice.")
            pcm = base64.b64decode(result.pop("wav"), validate=True)
            if not 44 < len(pcm) <= 2_000_000:
                raise RuntimeError("Invalid Windows speech audio size.")
            with wave.open(io.BytesIO(pcm)) as audio:
                if (audio.getnchannels() != 1 or audio.getsampwidth() != 2
                        or audio.getframerate() <= 0 or audio.getnframes() <= 0):
                    raise RuntimeError("Unsupported Windows speech PCM format.")
                duration = audio.getnframes() / audio.getframerate()
                if duration > 45:
                    raise RuntimeError("Windows speech audio exceeds its duration limit.")
            return pcm, {**result, "duration_s": duration, "backend": "windows-sapi"}
        finally:
            self.lock.release()

    def close(self):
        if self.process:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)
            self.process = None
