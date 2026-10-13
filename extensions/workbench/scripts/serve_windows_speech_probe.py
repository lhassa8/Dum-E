"""Real Windows speech API with no robot, task dispatch or microphone capture."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import uvicorn
from fastapi.responses import FileResponse

from physical_ai_lab.dume.app import make_api
from physical_ai_lab.dume.windows_speech import WindowsSpeech

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--port", type=int, default=9026)
args = parser.parse_args()
args.folder.mkdir(exist_ok=False)
texts = ["I'll bring you the screwdriver.",
         "Stopped. I have not confirmed completion of that task.",
         "The screwdriver is ready in the handoff tray.",
         "There isn't a stopped task to resume. Tell me what you'd like next.",
         "I'll put back the screwdriver.",
         "I couldn't reliably inspect that simulator snapshot."]
files = ["scripts/windows_speech_worker.ps1", "src/physical_ai_lab/dume/windows_speech.py",
         "src/physical_ai_lab/dume/app.py", "src/physical_ai_lab/dume/speech.py",
         "src/physical_ai_lab/dume/web/local-speech.mjs",
         "integrations/speech-vad/windows-dialogue.html"]
manifest = {"cases": [{"id": f"reply-{repeat}-{index}", "text": text}
                      for repeat in range(2) for index, text in enumerate(texts)],
            "maximum_reply_to_player_ms": 500,
            "scope": "Text-ready to Windows synthesis and HTMLAudio; no acoustic/arm qualification",
            "source_sha256": {file: hashlib.sha256((root / file).read_bytes()).hexdigest()
                              for file in files}}
(args.folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


async def idle():
    await asyncio.Event().wait()


async def state():
    return {"phase": "Speech probe, no arm", "busy": False, "model_status": "ready"}


async def records():
    return []


async def close():
    pass


agent = SimpleNamespace(log_path=args.folder / "events.jsonl", worker=idle, task_records=records,
                        active_id=None, last_result=None, messages=[],
                        controller=SimpleNamespace(state=state,
                                                   client=SimpleNamespace(aclose=close)))
api = make_api(agent, SimpleNamespace(poll=lambda: None), windows_speech=WindowsSpeech())


@api.get("/dialogue-benchmark")
async def page():
    return FileResponse(root / "integrations/speech-vad/windows-dialogue.html")


@api.get("/dialogue-manifest")
async def recipe():
    return manifest


@api.post("/dialogue-report")
async def save(data: dict):
    (args.folder / "browser.json").write_text(json.dumps(data, indent=2) + "\n")
    return {"saved": True}


uvicorn.run(api, host="127.0.0.1", port=args.port, log_level="warning")
