"""Fast commands must not mistake discussion, negation or conditions for action."""

import pytest

from physical_ai_lab.assistant.tool_routing import familiar_intent


@pytest.mark.parametrize(
    "text,action,tool",
    [
        ("Bring me the screwdriver, please.", "fetch", "screwdriver"),
        ("Could you hand me the wrench?", "fetch", "wrench"),
        ("Hand me the hammer, please.", "fetch", "hammer"),
        ("Please pass me a spanner.", "fetch", "wrench"),
        ("Would you please fetch my screwdriver?", "fetch", "screwdriver"),
        ("Actually can you hand me the hammer instead?", "fetch", "hammer"),
        ("Put the screwdriver back in its rack.", "return", "screwdriver"),
        ("Return the wrench to its rack, please.", "return", "wrench"),
        ("Please put my hammer back in the tool rack.", "return", "hammer"),
    ],
)
def test_supported_explicit_requests(text, action, tool):
    result = familiar_intent(text)
    assert result is not None and result.action == action and result.object == tool


@pytest.mark.parametrize(
    "text",
    [
        "Don't bring me the wrench.",
        "Please do not bring me the hammer.",
        "Could you not fetch the screwdriver?",
        "Bring me the wrench and the hammer.",
        "Bring me the screwdriver, then wave.",
        "If I ask, bring me the wrench.",
        "I said 'bring me the wrench'.",
        '"Bring me the wrench"',
        "Why did you bring me the wrench?",
        "Could you bring me the wrench tomorrow?",
        "Bring me the wrench if the screwdriver is missing.",
        "Use the screwdriver to turn a screw.",
        "Bring me a tool.",
        "Bring me the drill.",
        "Don't stop.",
        "Put it back.",
        "I need something for turning screws.",
        "What tool would you bring me?",
    ],
)
def test_other_utterances_require_language_understanding(text):
    assert familiar_intent(text) is None


def test_fast_route_bypasses_model_but_stop_invalidates_pending_command():
    from physical_ai_lab.assistant.app import Application

    app = Application(tools=True)
    app.model_status = "ready"
    app.chat("Please bring me a spanner.")
    assert app.requests.empty()
    kind, (epoch, job, intent) = app.commands.get_nowait()
    assert kind == "intent" and intent.object == "wrench"
    assert app.responsiveness["route"] == "familiar"
    app.stop()
    assert epoch != app.epoch
    assert app.interrupted["request"] == "Please bring me a spanner."


def test_negative_request_does_not_reuse_previous_semantic_tool_request():
    from physical_ai_lab.assistant.app import Application

    app = Application(tools=True)
    app.model_status = "ready"
    app.messages.append({"role": "user", "content": "I need something for turning screws."})
    app.chat("Don't bring me the wrench.")
    assert app.requests.empty()
    _, (_, _, intent) = app.commands.get_nowait()
    assert intent.action == "answer" and intent.object is None
    assert app.responsiveness["route"] == "decline"


def test_repeated_stop_does_not_reopen_stopping_or_invalidate_reset():
    from physical_ai_lab.assistant.app import Application

    app = Application(tools=True)
    app.model_status = "ready"
    app.chat("Bring me the hammer.")
    app.stop()
    epoch = app.epoch
    app.stop()
    assert app.epoch == epoch
    app.stop_event.clear()
    app.phase = "Stopped"
    app.stop()
    assert app.phase == "Stopped" and app.epoch == epoch and not app.stop_event.is_set()
