import asyncio
import threading
from types import SimpleNamespace

import httpx

from physical_ai_lab.dume.app import make_api


class VoiceProbe:
    voice = "Installed test voice"

    def __init__(self, delayed=False, fail=False):
        self.entered = threading.Event()
        self.release = threading.Event()
        if not delayed:
            self.release.set()
        self.fail = fail
        self.closed = False

    def prepare(self):
        pass

    def synthesize(self, text):
        self.entered.set()
        assert self.release.wait(3)
        if self.fail:
            raise RuntimeError("Native output failed")
        return b"RIFF-native-test", {"voice": self.voice, "duration_s": 1.5,
                                     "backend": "windows-sapi"}

    def close(self):
        self.closed = True


def api_for(tmp_path, voice, active=False):
    async def worker():
        await asyncio.Event().wait()

    async def cancel():
        voice.cancelled = True
        return {"cancelled": True}

    async def close():
        pass

    agent = SimpleNamespace(log_path=tmp_path / "events.jsonl", worker=worker,
                            active_id="active" if active else None, controller=SimpleNamespace(
                                client=SimpleNamespace(aclose=close)), cancel=cancel)
    return make_api(agent, SimpleNamespace(poll=lambda: None), windows_speech=voice)


def test_shutdown_cancels_active_arm_before_closing_speech_worker(tmp_path):
    voice = VoiceProbe()
    voice.cancelled = False
    original_close = voice.close

    def close_after_arm_stop():
        assert voice.cancelled, "Speech worker cleanup delayed physical cancellation"
        original_close()

    voice.close = close_after_arm_stop
    api = api_for(tmp_path, voice, active=True)

    async def run():
        async with api.router.lifespan_context(api):
            pass

    asyncio.run(run())
    assert voice.closed and voice.cancelled


def test_native_output_returns_audio_and_stop_expires_its_url(tmp_path):
    voice = VoiceProbe()
    api = api_for(tmp_path, voice)

    async def run():
        async with api.router.lifespan_context(api):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),
                                        base_url="http://test") as client:
                reply = (await client.post("/speak", json={"message": "A new reply."})).json()
                assert reply["backend"] == "windows-sapi"
                assert (await client.get(reply["audio"])).content == b"RIFF-native-test"
                assert (await client.post("/speech-stop")).status_code == 200
                assert (await client.get(reply["audio"])).status_code == 404

    asyncio.run(run())
    assert voice.closed


def test_stop_during_generation_remains_reachable_and_discards_late_audio(tmp_path):
    voice = VoiceProbe(delayed=True)
    api = api_for(tmp_path, voice)

    async def run():
        async with api.router.lifespan_context(api):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),
                                        base_url="http://test") as client:
                request = asyncio.create_task(client.post("/speak", json={"message": "Old reply."}))
                assert await asyncio.to_thread(voice.entered.wait, 1)
                response = await asyncio.wait_for(client.post("/stop"), timeout=.5)
                assert response.status_code == 200
                voice.release.set()
                result = (await request).json()
                assert result["superseded"] and not result["browser"]
                assert "audio" not in result and not (tmp_path / "speech-audio").exists()

    asyncio.run(run())


def test_configured_native_failure_does_not_fall_back_to_browser_synthesis(tmp_path):
    api = api_for(tmp_path, VoiceProbe(fail=True))

    async def run():
        async with api.router.lifespan_context(api):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),
                                        base_url="http://test") as client:
                response = await client.post("/speak", json={"message": "Reply."})
                assert response.status_code == 503
                assert "browser" not in response.json()

    asyncio.run(run())
