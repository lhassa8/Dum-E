"""Opt-in MLX idle-memory experiment; no model decoding, audio or robot actions."""

import time


class ModelResidency:
    def __init__(self, core, clock=time.monotonic):
        self.core, self.clock = core, clock
        info = core.device_info()
        active = int(core.get_active_memory())
        cap = min(int(info["max_recommended_working_set_size"]), int(info["memory_size"]) - 1)
        if not 0 < active <= cap:
            raise ValueError("Model allocations exceed the supported residency budget")
        self.limit = min(active + 256 * 2**20, cap)
        self.previous = core.set_wired_limit(self.limit)
        self.closed, self.count, self.last_ms = False, 0, 0.0
        try:
            self.scalar = core.zeros((1,))
            core.eval(self.scalar + 1)  # Prime only the tiny operation before Ready.
        except Exception:
            core.set_wired_limit(self.previous)
            raise
        self.next_refresh = clock() + 1.0

    def refresh(self):
        if self.closed or self.clock() < self.next_refresh:
            return
        started = time.perf_counter()
        self.core.eval(self.scalar + 1)
        self.last_ms = (time.perf_counter() - started) * 1000
        self.count += 1
        self.next_refresh = self.clock() + 1.0

    def profile(self):
        return {
            "experimental": True,
            "enabled": not self.closed,
            "limit_bytes": self.limit,
            "interval_s": 1.0,
            "refresh_count": self.count,
            "last_refresh_ms": self.last_ms,
        }

    def close(self):
        if not self.closed:
            try:
                self.core.synchronize()
            finally:
                try:
                    self.core.set_wired_limit(self.previous)
                finally:
                    self.closed = True
