"""Mac's installed speech synthesizer: local output, no microphone or cloud API."""

import subprocess


class Speech:
    def __init__(self):
        self.process = None
        self.last_text = None

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def speak(self, text):
        self.stop()
        self.last_text = text
        self.process = subprocess.Popen(
            ["/usr/bin/say"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.close()
        return {"started": True, "pid": self.process.pid}
