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


def test_voice_ready_waits_for_spoken_decode_and_failed_warmup_stays_unavailable(monkeypatch):
    from physical_ai_lab.dume import asr

    monkeypatch.setattr(asr, "model_path", lambda: "local-test-model")
    executable = asr.ffmpeg_path()
    monkeypatch.setattr(asr.shutil, "which", lambda name: executable)
    voice = SpeechInput()
    seen = []

    def decode(data):
        assert voice.status == "loading"
        # Bundled PCM speech must be usable by the original audio gates.
        audio = decode_audio(data)
        assert len(audio) > 16000 and np.sqrt(np.mean(audio**2)) > 0.003
        seen.append(True)
        return {"text": "Synthetic warmup"}

    monkeypatch.setattr(voice, "_recognize", decode)
    voice._prepare()
    assert seen and voice.status == "ready"
    assert voice.snapshot()["warmup_seconds"] is not None
    voice.close()
    failed = SpeechInput()

    def reject(data):
        raise ValueError("No confident speech")

    monkeypatch.setattr(failed, "_recognize", reject)
    failed._prepare()
    assert failed.status == "unavailable" and "No confident speech" in failed.error
    failed.close()


def test_speech_preparation_follows_language_allocation():
    from physical_ai_lab.dume.app import prepare_voice_after_language

    calls = []

    class Controller:
        async def state(self):
            calls.append("state")
            return {"model_status": "loading" if len(calls) == 1 else "ready"}

    class Speech:
        async def prepare(self):
            calls.append("prepare")

    asyncio.run(prepare_voice_after_language(Speech(), Controller()))
    assert calls == ["state", "state", "prepare"]


class RecognitionProbe:
    def snapshot(self):
        return {"status": "ready"}

    async def transcribe(self, data, interrupt=False):
        if data == b"invalid":
            raise ValueError("Invalid recording")
        return {"text": "Bring me the screwdriver."}


def test_reset_clears_pending_dialogue_only_when_idle(tmp_path):
    from physical_ai_lab.dume.app import make_api
    from physical_ai_lab.dume.interaction import InteractionCoordinator

    class Agent:
        log_path = tmp_path / "events.jsonl"
        messages, last_result, active_id = [], None, None
        busy = True
        resets = 0

        async def task_records(self):
            return []

        async def state(self):
            return {"model_status": "ready", "busy": self.busy}

        async def request(self, *args, **kwargs):
            self.resets += 1

    agent = Agent()
    agent.controller = agent
    agent.interaction = InteractionCoordinator(agent)
    agent.interaction.clarification = {"request": "Bring a tool", "question": "Which tool?"}
    api = make_api(agent, SimpleNamespace(poll=lambda: None), tools=True)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://testserver"
        ) as client:
            assert (await client.post("/reset")).status_code == 409
            assert agent.interaction.clarification and agent.interaction.epoch == 0
            assert agent.resets == 0
            agent.busy = False
            assert (await client.post("/reset")).status_code == 200
            assert agent.interaction.clarification is None
            assert agent.interaction.epoch == 1 and agent.resets == 1

    asyncio.run(run())


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
            assert response.json()["completed_at_s"] >= response.json()["received_at_s"]
            measured = await client.post(
                "/transcribe", content=b"voice", headers={
                    "content-type": "audio/webm",
                    "x-dume-capture-metrics":
                        '{"capture_ms":7440,"max_pending_frames":8,"unknown":123}',
                },
            )
            assert measured.json()["capture_metrics"] == {
                "capture_ms": 7440, "max_pending_frames": 8,
            }
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
            interruption = await client.post(
                "/transcribe",
                content=b"voice",
                headers={"content-type": "audio/webm", "x-dume-voice-mode": "interrupt"},
            )
            assert interruption.status_code == 200
            assert interruption.json()["voice_mode"] == "interrupt"
            assert await agent.task_records() == []
            assert (
                await client.post(
                    "/transcribe",
                    content=b"voice",
                    headers={"content-type": "audio/webm", "x-dume-voice-mode": "unknown"},
                )
            ).status_code == 400

    asyncio.run(run())


def test_local_speech_detector_assets_missing_unknown_and_available(tmp_path, monkeypatch):
    from physical_ai_lab.dume import app

    monkeypatch.setattr(app, "SPEECH_VAD", tmp_path)
    api = app.make_api(
        SimpleNamespace(),
        SimpleNamespace(poll=lambda: None),
        tools=True,
        speech_input=RecognitionProbe(),
    )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://testserver"
        ) as client:
            missing = await client.get("/speech-vad/silero_vad_v5.onnx")
            assert missing.status_code == 503
            assert "prepare_speech_vad.py" in missing.json()["detail"]
            assert (await client.get("/speech-vad/private.txt")).status_code == 404
            (tmp_path / "bundle.min.js").write_text("// probe")
            present = await client.get("/speech-vad/bundle.min.js")
            assert present.status_code == 200
            assert present.text == "// probe"
            assert present.headers["content-type"].startswith("application/javascript")
            assert (await client.get("/speech-detector.mjs")).status_code == 200

    asyncio.run(run())
