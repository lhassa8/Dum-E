"""Experimental explicit CPU recognizer for positive Stop only; not a device fallback."""

import time

from physical_ai_lab.assistant.tool_routing import is_stop_request

MODEL = "Systran/faster-whisper-tiny.en"
REVISION = "0d3d19a32d3338f10357c0889762bd8d64bbdeba"


class CpuStopRecognizer:
    def __init__(self):
        from faster_whisper import WhisperModel
        from huggingface_hub import snapshot_download

        started = time.monotonic()
        path = snapshot_download(MODEL, revision=REVISION, local_files_only=True, token=False,
                                 allow_patterns=["config.json", "model.bin", "tokenizer.json",
                                                 "vocabulary.txt"])
        self.model = WhisperModel(path, device="cpu", compute_type="int8", cpu_threads=8,
                                  num_workers=1, local_files_only=True)
        if self.model.model.device != "cpu":
            raise RuntimeError("Configured CPU Stop recognizer is not running on CPU.")
        self.load_seconds = time.monotonic() - started

    def inspect(self, audio):
        started = time.monotonic()
        segments, _ = self.model.transcribe(audio, language="en", temperature=0.0,
                                           condition_on_previous_text=False, beam_size=1,
                                           vad_filter=False)
        # Exactly the primary recognizer's original confidence gates. No Stop
        # prompt/hotword, context bias, lowered threshold, or action except Stop.
        accepted = [segment.text.strip() for segment in segments
                    if segment.no_speech_prob < 0.6 and segment.avg_logprob > -1.0]
        text = " ".join(accepted).strip()
        return {"text": text, "positive_stop": is_stop_request(text),
                "recognition_ms": (time.monotonic() - started) * 1000,
                "model": MODEL, "revision": REVISION, "device": "cpu", "compute_type": "int8"}
