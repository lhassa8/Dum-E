import asyncio
from types import SimpleNamespace

import httpx

from physical_ai_lab.dume import speech


def test_short_acknowledgment_echo_requires_start_and_expires(monkeypatch):
    monkeypatch.setattr(speech.sys, "platform", "linux")
    now = [100.0]
    monkeypatch.setattr(speech.time, "monotonic", lambda: now[0])
    output = speech.Speech()
    acknowledgment = output.speak("Let me check.")
    assert not output.is_echo("Let me check")
    output.started(acknowledgment["generation"])
    assert output.is_echo("Let me check")
    assert not output.is_echo("Stop")
    assert not output.is_echo("Put it back")
    output.speak("I will bring you the screwdriver.")
    assert output.is_echo("Let me check")
    now[0] += 3.01
    assert not output.is_echo("Let me check")


def test_acknowledgment_audio_is_optional_and_only_used_for_exact_neutral_phrase(
    tmp_path, monkeypatch
):
    from physical_ai_lab.dume import app

    monkeypatch.setattr(speech.sys, "platform", "linux")
    audio = tmp_path / "acknowledgment.wav"
    monkeypatch.setattr(app, "ACKNOWLEDGMENT_AUDIO", audio)
    api = app.make_api(SimpleNamespace(log_path=tmp_path / "events.jsonl"),
                       SimpleNamespace(poll=lambda: None))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),
                                    base_url="http://test") as client:
            assert (await client.get("/acknowledgment.wav")).status_code == 404
            missing = await client.post("/speak", json={"message": "Let me check."})
            assert "audio" not in missing.json() and missing.json()["browser"]
            audio.write_bytes(b"RIFF-local-audio-fixture")
            available = await client.post("/speak", json={"message": "Let me check."})
            assert available.json()["audio"] == "/acknowledgment.wav"
            response = await client.get("/acknowledgment.wav")
            assert response.content == audio.read_bytes()
            assert response.headers["content-type"] == "audio/wav"
            ordinary = await client.post("/speak", json={"message": "I will bring you the wrench."})
            assert "audio" not in ordinary.json()

    asyncio.run(run())


def test_browser_speech_requires_actual_start_and_rejects_stale_callbacks(monkeypatch):
    monkeypatch.setattr(speech.sys, "platform", "linux")
    output = speech.Speech()
    result = output.speak("I will bring you the screwdriver.")
    assert result["browser"] and not result["started"]
    assert not output.snapshot()["speaking"]
    assert not output.is_echo("I will bring you the screwdriver.")
    output.started(result["generation"])
    assert output.snapshot()["speaking"]
    assert output.is_echo("I will bring you the screwdriver.")
    assert not output.is_echo("Stop")
    output.stop()
    output.started(result["generation"])
    assert not output.snapshot()["speaking"]
    newer = output.speak("A wrench can tighten nuts.")
    output.started(newer["generation"])
    output.finished(result["generation"])
    assert output.snapshot()["speaking"]
    output.finished(newer["generation"])
    assert not output.snapshot()["speaking"]
