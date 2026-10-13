from physical_ai_lab.dume import speech


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
