"""Resource/cleanup contracts; actual idle-model performance needs real GPU tests."""

import pytest

from physical_ai_lab.assistant.residency import ModelResidency


class Core:
    def __init__(self, active=2**30):
        self.active, self.limit, self.evaluations = active, 0, 0

    def device_info(self):
        return {"max_recommended_working_set_size": 2 * 2**30, "memory_size": 4 * 2**30}

    def get_active_memory(self):
        return self.active

    def set_wired_limit(self, limit):
        previous, self.limit = self.limit, limit
        return previous

    def zeros(self, shape):
        return 0

    def eval(self, value):
        self.evaluations += 1

    def synchronize(self):
        pass


def test_residency_caps_budget_and_restores_it_on_close():
    core = Core()
    now = [0.0]
    keeper = ModelResidency(core, clock=lambda: now[0])
    assert core.limit <= core.device_info()["max_recommended_working_set_size"]
    keeper.refresh()
    assert core.evaluations == 1
    now[0] = 1.0
    keeper.refresh()
    assert core.evaluations == 2 and keeper.count == 1
    keeper.close()
    assert core.limit == 0
    now[0] = 10.0
    keeper.refresh()
    assert core.evaluations == 2


def test_unsupported_budget_never_changes_core_limit():
    core = Core(active=3 * 2**30)
    with pytest.raises(ValueError, match="budget"):
        ModelResidency(core)
    assert core.limit == 0 and core.evaluations == 0


def test_cleanup_restores_limit_even_if_gpu_synchronization_errors():
    core = Core()
    keeper = ModelResidency(core)

    def failing_sync():
        raise RuntimeError("GPU unavailable")

    core.synchronize = failing_sync
    with pytest.raises(RuntimeError, match="unavailable"):
        keeper.close()
    assert core.limit == 0 and keeper.closed


def fake_language(monkeypatch, tmp_path, core):
    import sys
    from types import SimpleNamespace

    from physical_ai_lab.assistant.language import LocalLanguage

    monkeypatch.setitem(sys.modules, "mlx", SimpleNamespace(core=core))
    monkeypatch.setitem(sys.modules, "mlx.core", core)
    monkeypatch.setitem(
        sys.modules, "mlx_lm", SimpleNamespace(load=lambda path: (object(), object()))
    )
    monkeypatch.setenv("WORKBENCH_PROMPT_CACHE", "0")
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("platform.mac_ver", lambda: ("27.0", (), "arm64"))
    return LocalLanguage(tmp_path)


def test_automatic_mode_enables_only_with_supported_budget(monkeypatch, tmp_path):
    monkeypatch.delenv("WORKBENCH_KEEP_MODEL_RESIDENT", raising=False)
    language = fake_language(monkeypatch, tmp_path, Core())
    assert language.residency is not None and language.residency_error is None
    language.residency.close()


def test_automatic_mode_falls_back_without_changing_unsupported_limit(monkeypatch, tmp_path):
    monkeypatch.delenv("WORKBENCH_KEEP_MODEL_RESIDENT", raising=False)
    core = Core(active=3 * 2**30)
    language = fake_language(monkeypatch, tmp_path, core)
    assert language.residency is None and "budget" in language.residency_error
    assert core.limit == 0


def test_explicit_mode_does_not_silently_ignore_unsupported_budget(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKBENCH_KEEP_MODEL_RESIDENT", "1")
    with pytest.raises(ValueError, match="budget"):
        fake_language(monkeypatch, tmp_path, Core(active=3 * 2**30))
