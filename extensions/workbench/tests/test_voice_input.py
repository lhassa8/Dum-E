"""Invalid audio and API isolation probes; real recognition is an independent live check."""

import asyncio
import io
import wave
from types import SimpleNamespace

import httpx
import numpy as np
import pytest

from physical_ai_lab.dume.asr import MAX_AUDIO_BYTES, SpeechInput, decode_audio


def recording(seconds=1, amplitude=0.0):
    output = io.BytesIO()
    with wave.open(output, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        t = np.arange(int(seconds * 16000)) / 16000
        file.writeframes((amplitude * np.sin(2 * np.pi * 440 * t) * 32767).astype("<i2").tobytes())
    return output.getvalue()


@pytest.mark.parametrize(
    "audio",
    [
        b"",
        b"not audio",
        recording(),
        recording(0.1, 0.2),
        recording(16, 0.2),
        b"x" * (MAX_AUDIO_BYTES + 1),
    ],
)
def test_unusable_audio_rejected(audio):
    with pytest.raises(ValueError):
        decode_audio(audio)


def test_voice_not_ready_cannot_transcribe():
    voice = SpeechInput()
    with pytest.raises(RuntimeError, match="loading"):
        asyncio.run(voice.transcribe(recording(1, 0.2)))
    voice.close()


class RecognitionProbe:
    def snapshot(self):
        return {"status": "ready"}

    async def transcribe(self, data):
        if data == b"invalid":
            raise ValueError("Invalid recording")
        return {"text": "Bring me the screwdriver."}


def test_transcription_never_submits_task(tmp_path):
    from physical_ai_lab.dume.app import make_api

    class Agent:
        log_path = tmp_path / "events.jsonl"
        messages, last_result, active_id = [], None, None

        async def task_records(self):
            return []

    agent = Agent()
    agent.controller = SimpleNamespace(
        state=lambda: asyncio.sleep(0, result={"model_status": "ready", "busy": False})
    )
    api = make_api(
        agent, SimpleNamespace(poll=lambda: None), tools=True, speech_input=RecognitionProbe()
    )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/transcribe", content=b"voice", headers={"content-type": "audio/webm"}
            )
            assert response.status_code == 200
            assert response.json()["text"] == "Bring me the screwdriver."
            assert await agent.task_records() == []
            invalid = await client.post(
                "/transcribe", content=b"invalid", headers={"content-type": "audio/webm"}
            )
            assert invalid.status_code == 422
            wrong = await client.post("/transcribe", content=b"voice")
            assert wrong.status_code == 415
            too_big = await client.post(
                "/transcribe",
                content=b"x" * (MAX_AUDIO_BYTES + 1),
                headers={"content-type": "audio/webm"},
            )
            assert too_big.status_code == 413
            external = await client.post(
                "/transcribe",
                content=b"voice",
                headers={"origin": "https://example.org", "content-type": "audio/webm"},
            )
            assert external.status_code == 403
            agent.controller.state = lambda: asyncio.sleep(
                0, result={"model_status": "ready", "busy": True}
            )
            busy = await client.post(
                "/transcribe", content=b"voice", headers={"content-type": "audio/webm"}
            )
            assert busy.status_code == 409

    asyncio.run(run())
