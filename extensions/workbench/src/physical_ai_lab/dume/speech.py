"""Mac's installed speech synthesizer: local output, no microphone or cloud API."""

import re
import subprocess
import time
from difflib import SequenceMatcher


class Speech:
    def __init__(self):
        self.process = None
        self.last_text = None
        self.finished_at = None

    def is_echo(self, text):
        if not self.last_text or not self.process:
            return False
        if self.process.poll() is not None:
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
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def speak(self, text):
        self.stop()
        self.last_text = text
        self.finished_at = None
        self.process = subprocess.Popen(
            ["/usr/bin/say"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.close()
        return {"started": True, "pid": self.process.pid}
