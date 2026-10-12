"""Official OpenPi SDK with bounded waits and task generations.

LIBERO outputs are controller inputs, never Panda joint positions. This module
operates no robot and certifies no model. Stop invalidates local actions and
closes the client worker; remote GPU computation itself may continue.
"""

import collections
import multiprocessing as mp
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import numpy as np


class PolicyInterrupted(RuntimeError):
    pass


@dataclass(frozen=True)
class LiberoAction:
    values: np.ndarray
    generation: int
    representation: str = "libero_osc_pose"


def _worker(pipe, endpoint):
    from openpi_client.websocket_client_policy import WebsocketClientPolicy

    try:
        policy = WebsocketClientPolicy(endpoint)
        pipe.send(("ready", policy.get_server_metadata()))
        while True:
            request, observation = pipe.recv()
            try:
                pipe.send(("result", request, policy.infer(observation)))
            except Exception as error:
                pipe.send(("error", request, str(error)))
    except (EOFError, BrokenPipeError):
        pass
    except Exception as error:
        try:
            pipe.send(("connection_error", str(error)))
        except (EOFError, BrokenPipeError):
            pass
    finally:
        pipe.close()


class PolicyConnection:
    """Persistent upstream connection; a stopped task cannot supply new actions."""

    def __init__(self, endpoint, connect_timeout=5.0, replan_steps=5):
        url = urlparse(endpoint)
        if url.scheme not in {"ws", "wss"} or not url.hostname or url.username or url.password:
            raise ValueError("Supply a ws:// or wss:// policy endpoint without credentials")
        if (
            url.query
            or url.fragment
            or not 0 < connect_timeout <= 30
            or not 1 <= replan_steps <= 50
        ):
            raise ValueError("Invalid endpoint or bounded connection configuration")
        self._endpoint = endpoint
        self._state = threading.Lock()
        self._inference = threading.Lock()
        self._generation = self._request = 0
        self._stopped = True
        self._closed = False
        self._actions = collections.deque()
        self._process = self._pipe = None
        self._retired = []
        self.replan_steps = replan_steps
        self.metadata = {}
        try:
            self._connect(connect_timeout)
        except Exception:
            self.close()
            raise

    def _check_task(self, generation):
        with self._state:
            if self._closed or (
                generation is not None and (self._stopped or generation != self._generation)
            ):
                raise PolicyInterrupted("Task was stopped or superseded")

    def _connect(self, timeout, generation=None):
        context = mp.get_context("spawn")
        pipe, child = context.Pipe()
        process = context.Process(target=_worker, args=(child, self._endpoint), daemon=True)
        with self._state:
            if self._closed or (
                generation is not None and (self._stopped or generation != self._generation)
            ):
                pipe.close()
                child.close()
                raise PolicyInterrupted("Task changed before connection")
            self._pipe, self._process = pipe, process
            process.start()
        child.close()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._check_task(generation)
            if pipe.poll(min(0.02, max(0, deadline - time.monotonic()))):
                message = pipe.recv()
                if message[0] != "ready" or not isinstance(message[1], dict):
                    raise RuntimeError("OpenPi connection failed: " + str(message))
                self.metadata = message[1]
                return
        raise TimeoutError("OpenPi connection/metadata timed out")

    def begin_task(self):
        # Superseding an active task also closes any blocked SDK request.
        with self._state:
            active = not self._stopped
        if active:
            self.stop()
        with self._state:
            if self._closed:
                raise RuntimeError("Policy connection is closed")
            self._generation += 1
            self._stopped = False
            self._actions.clear()
            return self._generation

    def stop(self):
        """Invalidate first, then terminate blocked SDK IO without waiting for GPU."""
        with self._state:
            self._generation += 1
            self._stopped = True
            self._actions.clear()
            process, pipe = self._process, self._pipe
            self._process = self._pipe = None
            if process is not None:
                self._retired.append(process)
        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=0)
        if pipe is not None:
            pipe.close()

    def _send(self, pipe, payload, generation, deadline):
        # Large camera frames can fill IPC if the SDK worker stalls. Keep that
        # write outside the control thread so Stop and the deadline still apply.
        sent = threading.Event()
        errors = []

        def write():
            try:
                pipe.send(payload)
            except (OSError, ValueError) as error:
                errors.append(error)
            finally:
                sent.set()

        sender = threading.Thread(target=write, daemon=True)
        sender.start()
        while not sent.wait(min(0.02, max(0, deadline - time.monotonic()))):
            self._check_task(generation)
            if time.monotonic() >= deadline:
                raise TimeoutError("Policy observation transfer timed out")
        self._check_task(generation)
        if errors:
            raise errors[0]

    def infer(self, observation, generation, timeout=5.0):
        if not 0 < timeout <= 30:
            raise ValueError("Inference timeout must be bounded")
        if not self._inference.acquire(blocking=False):
            raise RuntimeError("A policy request is already being processed")
        try:
            started = time.perf_counter()
            deadline = time.monotonic() + timeout
            self._check_task(generation)
            if self._process is None:
                self._connect(max(0.001, deadline - time.monotonic()), generation)
            with self._state:
                self._request += 1
                request, pipe = self._request, self._pipe
            self._check_task(generation)
            self._send(pipe, (request, observation), generation, deadline)
            while time.monotonic() < deadline:
                self._check_task(generation)
                if not pipe.poll(min(0.02, max(0, deadline - time.monotonic()))):
                    continue
                message = pipe.recv()
                if len(message) < 3 or message[0] not in {"result", "error"}:
                    raise RuntimeError("Unexpected policy worker message")
                if message[1] != request:
                    continue
                if message[0] == "error":
                    raise RuntimeError(message[2])
                result = message[2]
                if not isinstance(result, dict):
                    raise ValueError("Expected a policy result dictionary")
                actions = np.asarray(result.get("actions"))
                if (
                    actions.ndim != 2
                    or actions.shape[1] != 7
                    or not self.replan_steps <= len(actions) <= 50
                    or not np.issubdtype(actions.dtype, np.floating)
                    or not np.isfinite(actions).all()
                ):
                    raise ValueError("Expected a finite LIBERO action chunk shaped horizon x 7")
                with self._state:
                    if self._closed or self._stopped or generation != self._generation:
                        raise PolicyInterrupted("Reply arrived after Stop/task change")
                    self._actions.extend(
                        (generation, a.copy()) for a in actions[: self.replan_steps]
                    )
                return {
                    "round_trip_ms": (time.perf_counter() - started) * 1000,
                    "server_timing": result.get("server_timing", {}),
                    "queued_actions": self.replan_steps,
                    "action_representation": "LIBERO OSC controller inputs; not robot joints",
                }
            raise TimeoutError("Policy inference timed out; actions invalidated")
        except TimeoutError:
            self._check_task(generation)
            self.stop()
            raise
        except (EOFError, OSError) as error:
            self._check_task(generation)
            self.stop()
            raise RuntimeError("Policy connection or action contract failed") from error
        except ValueError:
            self._check_task(generation)
            self.stop()
            raise
        except RuntimeError:
            with self._state:
                current = generation == self._generation and not self._stopped
            if current:
                self.stop()
            raise
        finally:
            self._inference.release()

    def take_action(self, generation):
        with self._state:
            if self._stopped or generation != self._generation or not self._actions:
                return None
            queued_generation, action = self._actions.popleft()
            return LiberoAction(action, generation) if queued_generation == generation else None

    def close(self):
        self.stop()
        with self._state:
            self._closed = True
        for process in self._retired:
            process.join(timeout=0.2)
            if process.is_alive():
                process.kill()
                process.join(timeout=0.2)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
