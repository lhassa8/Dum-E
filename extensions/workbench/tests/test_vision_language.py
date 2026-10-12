"""Vision transport cannot become robot commands or silently change models."""

import copy
import io
import json

import httpx
import pytest
from PIL import Image

from physical_ai_lab.assistant.vision_language import (
    TOOLS,
    LMStudioVision,
    parse_compact,
    parse_observation,
)

MODEL = "example/vision-model"
EMPTY = {name: {"visible": False, "center": None} for name in TOOLS}


def frame():
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "black").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_vision_sends_only_rgb_and_catalog_and_accepts_configurable_model():
    def respond(request):
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == MODEL and body["stream"] is False
        assert set(body) == {
            "model",
            "temperature",
            "reasoning_effort",
            "max_tokens",
            "stream",
            "messages",
            "response_format",
        }
        assert len(body["messages"]) == 2
        parts = body["messages"][-1]["content"]
        assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        assert "positions_m" not in request.content.decode()
        return httpx.Response(
            200,
            json={
                "model": MODEL,
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(EMPTY)}}],
            },
        )

    model = LMStudioVision(MODEL, transport=httpx.MockTransport(respond))
    try:
        result = model.observe(frame())
        assert result["tools"] == EMPTY and result["model"] == MODEL
    finally:
        model.close()
    assert model.client.is_closed


@pytest.mark.parametrize(
    "change",
    [
        "nan",
        "out_of_bounds",
        "bool_center",
        "uncertain_center",
        "action",
        "missing",
        "presence_string",
    ],
)
def test_malformed_observations_cannot_become_locations(change):
    value = copy.deepcopy(EMPTY)
    if change in {"nan", "out_of_bounds", "bool_center"}:
        value["wrench"] = {
            "visible": True,
            "center": {
                "nan": [float("nan"), 0.5],
                "out_of_bounds": [1.1, 0.5],
                "bool_center": [True, 0.5],
            }[change],
        }
    elif change == "uncertain_center":
        value["wrench"]["center"] = [0.5, 0.5]
    elif change == "action":
        value["action"] = "fetch"
    elif change == "missing":
        del value["wrench"]
    else:
        value["wrench"]["visible"] = "false"
    with pytest.raises(ValueError):
        parse_observation(json.dumps(value))


@pytest.mark.parametrize(
    "model_name,reason,calls",
    [("substitute/model", "stop", []), (MODEL, "length", []), (MODEL, "stop", [{"name": "fetch"}])],
)
def test_model_substitution_truncation_and_actions_are_rejected(model_name, reason, calls):
    model = LMStudioVision(
        MODEL,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "model": model_name,
                    "choices": [
                        {
                            "finish_reason": reason,
                            "message": {"content": json.dumps(EMPTY), "tool_calls": calls},
                        }
                    ],
                },
            )
        ),
    )
    try:
        with pytest.raises(RuntimeError):
            model.observe(frame())
    finally:
        model.close()


def test_timeout_and_bad_input_do_not_retry_or_fall_back():
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("vision timeout")

    model = LMStudioVision(MODEL, transport=httpx.MockTransport(fail))
    try:
        with pytest.raises(ValueError):
            model.observe(b"not a jpeg")
        assert not calls
        with pytest.raises(httpx.ReadTimeout):
            model.observe(frame())
        assert len(calls) == 1
    finally:
        model.close()


def test_compact_centers_have_the_same_observation_semantics():
    compact = {"screwdriver": [0.25, 0.75], "wrench": None, "hammer": [0.75, 0.5]}
    result = parse_compact(json.dumps(compact))
    assert result == {
        name: {"visible": center is not None, "center": center} for name, center in compact.items()
    }
    with pytest.raises(ValueError):
        parse_compact(json.dumps({**compact, "action": "fetch"}))
    with pytest.raises(ValueError):
        parse_compact(json.dumps({**compact, "wrench": [1.1, 0.5]}))


def test_compact_transport_uses_bounded_short_output():
    def respond(request):
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 128
        assert payload["response_format"]["json_schema"]["schema"]["properties"]["wrench"]["anyOf"]
        return httpx.Response(
            200,
            json={
                "model": MODEL,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps({name: None for name in TOOLS})},
                    }
                ],
            },
        )

    model = LMStudioVision(MODEL, compact=True, transport=httpx.MockTransport(respond))
    try:
        assert model.observe(frame())["tools"] == EMPTY
    finally:
        model.close()


def test_declared_grid_conversion_preserves_axes_and_rejects_wrong_units():
    raw = {"screwdriver": [485, 302], "wrench": None, "hammer": [486, 729]}
    value = parse_compact(json.dumps(raw), "grid1000_yx")
    assert value["screwdriver"]["center"] == [0.302, 0.485]
    assert value["hammer"]["center"] == [0.729, 0.486]
    assert value["wrench"] == {"visible": False, "center": None}
    # No auto-unit guessing: the original normalized contract still rejects it.
    with pytest.raises(ValueError):
        parse_compact(json.dumps(raw))
    for bad in [[1001, 302], [485, True], [float("nan"), 302]]:
        with pytest.raises(ValueError):
            parse_compact(json.dumps({**raw, "screwdriver": bad}), "grid1000_yx")
    with pytest.raises(ValueError):
        LMStudioVision(MODEL, compact=False, coordinates="grid1000_yx")
