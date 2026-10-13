"""Independent real-audio -> local ASR -> original task bus -> native physics check."""

import argparse
import hashlib
import io
import json
import math
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--message", default="Bring me the screwdriver, please.")
    parser.add_argument("--audio", type=Path, help="Existing saved audio for Windows/WSL checks")
    parser.add_argument("--audio-source", default="Saved audio; no microphone recording")
    parser.add_argument("--return-after-delivery", action="store_true")
    parser.add_argument("--expect-model-interpretation", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.audio and not args.audio.is_file():
        parser.error("The saved audio file does not exist")
    if args.audio is None and not Path("/usr/bin/say").is_file():
        parser.error("Use --audio with a saved speech clip on Windows/WSL")
    args.output.mkdir(parents=True, exist_ok=False)
    with httpx.Client(base_url=args.url, timeout=30, trust_env=False) as client:

        def state():
            response = client.get("/state")
            response.raise_for_status()
            return response.json()

        def wait_ready():
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                snapshot = state()
                if not snapshot["busy"]:
                    return snapshot
                time.sleep(0.15)
            raise TimeoutError("Dum-E did not become idle")

        def run_task(text):
            result = client.post("/chat", json={"message": text})
            result.raise_for_status()
            task_id = result.json()["task_id"]
            deadline = time.monotonic() + 90
            trace = []
            while time.monotonic() < deadline:
                snapshot = state()
                trace.append({"phase": snapshot["phase"], "objects": snapshot["objects"]})
                task = next((t for t in snapshot["tasks"] if t["task_id"] == task_id), None)
                if task and task["status"] in {"completed", "failed", "cancelled"}:
                    assert snapshot["last_result"]["task_id"] == task_id
                    return snapshot, trace
                time.sleep(0.10)
            raise TimeoutError("Voice delivery task timed out")

        initial = wait_ready()
        assert initial["speech_input"]["status"] == "ready"
        # Return an already delivered tool through physics instead of resetting it.
        for tool, location in initial["inventory"].items():
            if location.startswith("handoff tray"):
                returned, _ = run_task(f"Put the {tool} back in its rack, please.")
                assert returned["last_result"]["physical_success"]
        initial = wait_ready()
        count = len(initial["tasks"])
        silent = io.BytesIO()
        with wave.open(silent, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 32000)
        silence = client.post(
            "/transcribe", content=silent.getvalue(), headers={"Content-Type": "audio/wav"}
        )
        assert silence.status_code == 422
        assert len(state()["tasks"]) == count
        with tempfile.TemporaryDirectory() as directory:
            if args.audio:
                recording = args.audio
                source = args.audio_source
            else:
                request = Path(directory) / "request.txt"
                recording = Path(directory) / "request.aiff"
                request.write_text(args.message + "\n")
                subprocess.run(
                    ["/usr/bin/say", "-o", str(recording), "-f", str(request)], check=True
                )
                source = "Native Mac synthesized speech; no microphone recording"
            payload = recording.read_bytes()
            recognition_started = time.monotonic()
            response = client.post(
                "/transcribe",
                content=payload,
                headers={
                    "Content-Type": "audio/aiff" if recording.suffix == ".aiff" else "audio/wav"
                },
            )
            recognition_ms = (time.monotonic() - recognition_started) * 1000
        response.raise_for_status()
        recognized = response.json()
        if "screwdriver" in args.message.lower():
            assert "screwdriver" in recognized["text"].lower()
        assert len(state()["tasks"]) == count  # Recognition itself never actuates.
        final, trace = run_task(recognized["text"])
        result = final["last_result"]
        if args.expect_model_interpretation:
            assert "interpretation_started_ms" in final["responsiveness"]
        assert result["physical_success"] and result["status"] == "completed"
        assert result["intent"]["action"] == "fetch"
        assert result["intent"]["object"] == "screwdriver"
        actual = final["objects"]["screwdriver"]
        target = final["targets"]["handoff"]
        error = math.dist(actual[:2], target[:2])
        lift = (
            max(frame["objects"]["screwdriver"][2] for frame in trace)
            - initial["objects"]["screwdriver"][2]
        )
        assert error < 0.035 and actual[2] < 0.04 and lift > 0.08
        return_result = None
        if args.return_after_delivery:
            returned, _ = run_task("Put the screwdriver back in its rack.")
            assert returned["last_result"]["physical_success"]
            assert returned["last_result"]["intent"]["action"] == "return"
            assert returned["last_result"]["intent"]["object"] == "screwdriver"
            assert (
                math.dist(
                    returned["objects"]["screwdriver"][:2], initial["objects"]["screwdriver"][:2]
                )
                < 0.035
            )
            return_result = returned["last_result"]
        (args.output / "verification.json").write_text(
            json.dumps(
                {
                    "source": source,
                    "audio_sha256": hashlib.sha256(payload).hexdigest(),
                    "tool_control": final.get("tool_control", "baseline"),
                    "requested_speech": args.message,
                    "recognition_ms": recognition_ms,
                    "native_responsiveness": final["responsiveness"],
                    "model": final["language_model"],
                    "recognition": recognized,
                    "result": result,
                    "actual_position_m": actual,
                    "target_m": target,
                    "observed_lift_m": lift,
                    "distance_m": error,
                    "silence_status": silence.status_code,
                    "trace": trace,
                    "return_result": return_result,
                },
                indent=2,
            )
            + "\n"
        )
        print(
            f"PASS: {recognized['text']} — physical screwdriver delivery, "
            f"{error * 1000:.1f} mm error, {lift * 1000:.1f} mm lift."
        )


if __name__ == "__main__":
    main()
