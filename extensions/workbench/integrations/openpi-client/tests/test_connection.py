"""Official wire protocol, late replies, chunk validation and bounded failures."""

import os
import signal
import socket
import threading
import time

import numpy as np
import pytest
from protocol_fixture import FixtureServer, SyntheticPolicy, observation

from dume_pretrained.connection import PolicyConnection, PolicyInterrupted
from dume_pretrained.observations import libero_observation


def test_actual_upstream_connection_and_stop_flush_queued_chunk():
    with FixtureServer(SyntheticPolicy()) as server:
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            assert client.metadata["model_weights_loaded"] is False
            generation = client.begin_task()
            evidence = client.infer(observation(), generation)
            assert evidence["queued_actions"] == 5
            assert client.take_action(generation).values[0] == pytest.approx(0.1)
            client.stop()
            assert client.take_action(generation) is None


def test_stop_during_inference_and_new_task_rejects_late_reply():
    policy = SyntheticPolicy(delay=0.3)
    with FixtureServer(policy) as server:
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            generation = client.begin_task()
            outcomes = []

            def pending():
                try:
                    client.infer(observation(), generation)
                except PolicyInterrupted:
                    outcomes.append("interrupted")

            worker = threading.Thread(target=pending)
            worker.start()
            assert policy.started.wait(2)
            start = time.perf_counter()
            client.stop()
            worker.join(timeout=0.1)
            assert not worker.is_alive() and outcomes == ["interrupted"]
            assert time.perf_counter() - start < 0.1
            assert client.take_action(generation) is None
            current = client.begin_task()
            obs = observation()
            obs["prompt"] = "second task"
            client.infer(obs, current)
            assert client.take_action(current).values[0] == pytest.approx(0.2)
            assert client.take_action(generation) is None


def test_invalid_chunk_and_timeout_never_queue_actions():
    with FixtureServer(SyntheticPolicy(bad=True)) as server:
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            generation = client.begin_task()
            with pytest.raises(ValueError, match="finite LIBERO"):
                client.infer(observation(), generation)
            assert client.take_action(generation) is None
    with FixtureServer(SyntheticPolicy(delay=0.3)) as server:
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            generation = client.begin_task()
            with pytest.raises(TimeoutError):
                client.infer(observation(), generation, timeout=0.04)
            assert client.take_action(generation) is None


def test_unavailable_server_has_a_bounded_connection_wait():
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        started = time.perf_counter()
        with pytest.raises(TimeoutError):
            PolicyConnection(f"ws://127.0.0.1:{port}", connect_timeout=0.2)
        assert time.perf_counter() - started < 1


def test_bad_reply_also_invalidates_previously_queued_actions():
    policy = SyntheticPolicy()
    with FixtureServer(policy) as server:
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            generation = client.begin_task()
            client.infer(observation(), generation)
            policy.bad = True
            with pytest.raises(ValueError, match="finite LIBERO"):
                client.infer(observation(), generation)
            assert client.take_action(generation) is None


@pytest.mark.skipif(not hasattr(signal, "SIGSTOP"), reason="POSIX fault injection")
def test_stalled_sdk_worker_cannot_block_observation_timeout():
    with FixtureServer(SyntheticPolicy()) as server:
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            generation = client.begin_task()
            worker = client._process
            os.kill(worker.pid, signal.SIGSTOP)
            try:
                started = time.perf_counter()
                with pytest.raises(TimeoutError):
                    client.infer(observation(), generation, timeout=0.08)
                assert time.perf_counter() - started < 0.3
                assert client.take_action(generation) is None
            finally:
                if worker.is_alive():
                    os.kill(worker.pid, signal.SIGCONT)


def test_probe_preserves_observed_handshake_when_inference_fails(tmp_path, monkeypatch):
    import json
    import sys

    from dume_pretrained.probe import main

    raw = tmp_path / "raw.npz"
    image = np.zeros((224, 224, 3), np.uint8)
    np.savez(
        raw,
        agentview_image=image,
        robot0_eye_in_hand_image=image,
        robot0_eef_pos=np.zeros(3),
        robot0_eef_quat=[0, 0, 0, 1],
        robot0_gripper_qpos=np.zeros(2),
    )
    with FixtureServer(SyntheticPolicy(bad=True)) as server:
        output = tmp_path / "result"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "dume-policy-probe",
                "--endpoint",
                f"ws://127.0.0.1:{server.port}",
                "--output",
                str(output),
                "--observation-npz",
                str(raw),
            ],
        )
        with pytest.raises(SystemExit, match="1"):
            main()
        evidence = json.loads((output / "probe.json").read_text())
        assert evidence["connected"] is True and evidence["passed"] is False
        assert evidence["model_identity_verified"] is False
        assert evidence["closed_loop_demonstrated"] is False


def test_libero_image_rotation_and_pose_units_are_explicit():
    image = np.zeros((224, 224, 3), np.uint8)
    image[0, 0] = [255, 10, 20]
    raw = {
        "agentview_image": image,
        "robot0_eye_in_hand_image": image,
        "robot0_eef_pos": [0.4, -0.2, 0.3],
        "robot0_eef_quat": [0, 0, np.sin(0.25), np.cos(0.25)],
        "robot0_gripper_qpos": [0.02, 0.02],
    }
    obs = libero_observation(raw, "pick up the bowl")
    np.testing.assert_array_equal(obs["observation/image"][-1, -1], [255, 10, 20])
    np.testing.assert_allclose(obs["observation/state"], [0.4, -0.2, 0.3, 0, 0, 0.5, 0.02, 0.02])
    raw["robot0_eef_quat"] = [0, 0, 0, 0]
    with pytest.raises(ValueError, match="measurements"):
        libero_observation(raw, "pick up the bowl")


def test_upstream_server_fixture_is_unmodified_and_pinned():
    import hashlib
    import json
    from pathlib import Path

    folder = Path(__file__).parents[1] / "fixtures"
    provenance = json.loads((folder / "provenance.json").read_text())
    assert provenance["commit"] == "215abfb217dbac7d5f1273282331b9b1866c0479"
    assert (
        hashlib.sha256((folder / "upstream_websocket_policy_server.py").read_bytes()).hexdigest()
        == provenance["sha256"]
    )
