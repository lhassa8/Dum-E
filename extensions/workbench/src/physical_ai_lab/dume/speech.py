"""Local output: macOS say or the browser's installed local voices."""

import re
import subprocess
import sys
import time
from difflib import SequenceMatcher


class Speech:
    def __init__(self):
        self.process = None
        self.last_text = None
        self.finished_at = None
        self.browser_deadline = 0
        self.generation = 0
        self.has_started = False
        self.acknowledgment_started_at = None
        self.audio_duration = None

    def snapshot(self):
        return {
            "last_text": self.last_text,
            "speaking": bool(self.process and self.process.poll() is None)
            or time.monotonic() < self.browser_deadline,
            "backend": "say" if sys.platform == "darwin" else "browser-local",
        }

    def finished(self, generation):
        if generation == self.generation:
            self.browser_deadline = 0
            self.finished_at = time.monotonic()
            return True
        return False

    def started(self, generation):
        if generation == self.generation:
            self.has_started = True
            self.browser_deadline = time.monotonic() + (
                self.audio_duration + 2 if self.audio_duration is not None else 40
            )
            if self.last_text == "Let me check.":
                self.acknowledgment_started_at = time.monotonic()
            return True
        return False

    def is_echo(self, text):
        normalized = " ".join(re.sub(r"[^a-z0-9\s]", " ", text.lower()).split())
        if (normalized == "let me check" and self.acknowledgment_started_at is not None
                and time.monotonic() - self.acknowledgment_started_at < 3):
            return True
        if not self.last_text or not (self.has_started or self.process):
            return False
        if not self.snapshot()["speaking"]:
            if self.finished_at is None:
                self.finished_at = time.monotonic()
            if time.monotonic() - self.finished_at > 2:
                return False

        def normalize(s):
            return " ".join(re.sub(r"[^a-z0-9\s]", " ", s.lower()).split())

        heard, spoken = normalize(text), normalize(self.last_text)
        # Stop is handled independently. Don't reject a short real user command
        # because its tool name is also present in the assistant's reply.
        return len(heard.split()) >= 4 and (
            heard in spoken or SequenceMatcher(None, heard, spoken).ratio() >= 0.85
        )

    def stop(self):
        self.generation += 1
        self.browser_deadline = 0
        self.finished_at = time.monotonic()
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def speak(self, text):
        self.stop()
        self.audio_duration = None
        self.last_text = text
        self.finished_at = None
        self.has_started = False
        if sys.platform != "darwin":
            return {"started": False, "browser": True, "generation": self.generation}
        self.has_started = True
        self.process = subprocess.Popen(
            ["/usr/bin/say"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.close()
        return {"started": True, "pid": self.process.pid}
