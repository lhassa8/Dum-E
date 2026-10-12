"""Measure official-wire transport only: synthetic policy, no arm or GPU model."""

import argparse
import json
import platform
import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from protocol_fixture import FixtureServer, SyntheticPolicy, observation  # noqa: E402

from dume_pretrained.connection import PolicyConnection, PolicyInterrupted  # noqa: E402


def summarize(values):
    return {
        "samples": len(values),
        "median_ms": float(np.median(values)),
        "p95_ms": float(np.percentile(values, 95)),
        "maximum_ms": max(values),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    policy = SyntheticPolicy()
    timings, stops, reconnects = [], [], []
    with FixtureServer(policy) as server:
        started = time.perf_counter()
        with PolicyConnection(f"ws://127.0.0.1:{server.port}") as client:
            connect_ms = (time.perf_counter() - started) * 1000
            metadata = client.metadata
            generation = client.begin_task()
            for _ in range(20):
                timings.append(client.infer(observation(), generation)["round_trip_ms"])
                for _ in range(5):
                    assert client.take_action(generation).values[0] == np.float32(0.1)
                assert client.take_action(generation) is None
            policy.delay = 0.3
            for _ in range(5):
                policy.started.clear()
                outcomes = []

                def pending():
                    try:
                        client.infer(observation(), generation)
                    except PolicyInterrupted:
                        outcomes.append("interrupted")

                thread = threading.Thread(target=pending)
                thread.start()
                assert policy.started.wait(2)
                started = time.perf_counter()
                client.stop()
                thread.join(timeout=0.1)
                stops.append((time.perf_counter() - started) * 1000)
                assert not thread.is_alive() and outcomes == ["interrupted"]
                assert client.take_action(generation) is None
                generation = client.begin_task()
                obs = observation()
                obs["prompt"] = "second task"
                started = time.perf_counter()
                client.infer(obs, generation)
                reconnects.append((time.perf_counter() - started) * 1000)
                for _ in range(5):
                    assert client.take_action(generation).values[0] == np.float32(0.2)
                assert client.take_action(generation) is None
    report = {
        "scope": "Official OpenPi SDK/server wire protocol with synthetic policy; no robot motion",
        "upstream_commit": "215abfb217dbac7d5f1273282331b9b1866c0479",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "server_metadata": metadata,
        "model_weights_loaded": False,
        "pretrained_policy_latency_measured": False,
        "physical_stop_measured": False,
        "initial_connection_ms": connect_ms,
        "warm_round_trip": summarize(timings),
        "stop_and_local_request_exit": summarize(stops),
        "reconnect_and_next_reply_with_300ms_synthetic_delay": summarize(reconnects),
        "queued_actions_flushed": True,
        "old_task_actions_accepted_after_stop": 0,
        "warm_round_trip_ms": timings,
        "stop_and_local_request_exit_ms": stops,
        "remote_computation_may_continue": True,
    }
    (args.output / "transport.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("_ms")}, indent=2))


if __name__ == "__main__":
    main()
