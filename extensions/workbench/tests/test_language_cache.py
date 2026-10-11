"""Cache isolation contract; real inference is judged by fixed dialogue fixtures."""

import json
import sys
from types import SimpleNamespace

from physical_ai_lab.assistant.language import LocalLanguage


def test_request_cache_does_not_retain_scene_or_dialogue(monkeypatch):
    class Tokenizer:
        bos_token = None

        def apply_chat_template(self, messages, **kwargs):
            return json.dumps(messages)

        def encode(self, text, **kwargs):
            return list(text.encode())

    language = LocalLanguage.__new__(LocalLanguage)
    language.system = "Fixed instructions"
    language.model = object()
    language.tokenizer = Tokenizer()
    language.parser = json.loads
    language.prefix_tokens = list(b'[{"role": "system", "content": "Fixed instructions')
    original = SimpleNamespace(state={"recurrent": [7]}, nbytes=128)
    language.prefix_cache = [original]
    language.prefix_prepare_ms = 12
    seen = []

    def generate(model, tokenizer, prompt, prompt_cache, **kwargs):
        seen.append((bytes(prompt).decode(), prompt_cache))
        if prompt_cache is not None:
            assert prompt_cache[0].state["recurrent"] == [7]
            prompt_cache[0].state["recurrent"].append(99)
        # The parser must see complete JSON, not a partial streaming response.
        for part in ['{"action":', '"answer"}']:
            yield SimpleNamespace(
                text=part,
                prompt_tokens=len(prompt),
                prompt_tps=100,
                generation_tokens=2,
                generation_tps=100,
                peak_memory=1,
                finish_reason="stop",
            )

    monkeypatch.setitem(sys.modules, "mlx_lm", SimpleNamespace(stream_generate=generate))
    monkeypatch.setitem(
        sys.modules, "mlx_lm.sample_utils", SimpleNamespace(make_sampler=lambda **kwargs: None)
    )
    first, _ = language.interpret(
        "Which tool?", [{"role": "assistant", "content": "First context"}], {"rack": 1}
    )
    assert first == {"action": "answer"}
    language.interpret(
        "Wrench", [{"role": "assistant", "content": "Different context"}], {"rack": 2}
    )
    assert original.state == {"recurrent": [7]}
    assert seen[0][1] is not seen[1][1]
    assert "First context" in seen[0][0] and '\\"rack\\": 1' in seen[0][0]
    assert "Different context" in seen[1][0] and "First context" not in seen[1][0]
    assert '\\"rack\\": 2' in seen[1][0] and '\\"rack\\": 1' not in seen[1][0]
    assert language.last_profile["cached_prefix_tokens"] == len(language.prefix_tokens)
    # A template or instruction change must safely fall back to a full prompt.
    language.system = "Changed instructions"
    language.interpret("Hello", observations={"rack": 3})
    assert seen[2][1] is None
    assert "Changed instructions" in seen[2][0]
    assert language.last_profile["cached_prefix_tokens"] == 0
