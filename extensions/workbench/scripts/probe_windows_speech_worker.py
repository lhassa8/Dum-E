"""Exercise the installed Windows voice from WSL without speaker or microphone use."""

import base64
import hashlib
import io
import json
import subprocess
import time
import uuid
import wave
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / "runs/windows-speech-worker-001"
output.mkdir(exist_ok=False)
script = subprocess.check_output(["wslpath", "-w", str(root / "scripts/windows_speech_worker.ps1")],
                                 text=True).strip()
started = time.perf_counter()
worker = subprocess.Popen([
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
    "-NoProfile", "-File", script,
], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8")
rows = []
try:
    ready = json.loads(worker.stdout.readline())
    assert ready["kind"] == "ready" and ready["local"] is True
    cold_ms = (time.perf_counter() - started) * 1000
    texts = ["Let me check.", "I'll bring you the screwdriver.",
             "Stopped. I have not confirmed completion of that task.",
             "The screwdriver is ready in the handoff tray.",
             "There isn't a stopped task to resume. Tell me what you'd like next.",
             "I'll put back the screwdriver."]
    for repeat in range(2):
        for index, text in enumerate(texts):
            request_id = uuid.uuid4().hex
            started = time.perf_counter()
            worker.stdin.write(json.dumps({"id": request_id, "text": text}) + "\n")
            worker.stdin.flush()
            reply = json.loads(worker.stdout.readline())
            assert reply["kind"] == "audio" and reply["id"] == request_id and reply["local"]
            pcm = base64.b64decode(reply.pop("wav"), validate=True)
            with wave.open(io.BytesIO(pcm)) as audio:
                duration = audio.getnframes() / audio.getframerate()
                assert duration > .35 and audio.getsampwidth() == 2
            file = f"reply-{repeat}-{index}.wav"
            (output / file).write_bytes(pcm)
            rows.append({**reply, "text": text, "file": file, "duration_s": duration,
                         "sha256": hashlib.sha256(pcm).hexdigest(),
                         "roundtrip_ms": (time.perf_counter() - started) * 1000})
    (output / "results.json").write_text(json.dumps({"ready": ready, "cold_ms": cold_ms,
                                                   "rows": rows}, indent=2) + "\n")
    print(json.dumps({"voice": ready["voice"], "cold_ms": cold_ms, "count": len(rows),
                      "roundtrip_ms": [round(row["roundtrip_ms"], 1) for row in rows]}))
finally:
    worker.stdin.close()
    worker.wait(timeout=15)
    if worker.returncode:
        raise RuntimeError(worker.stderr.read()[:1000])
