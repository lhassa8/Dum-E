"""Bounded mono float32 decoding with the installed PyAV/FFmpeg libraries."""

import io

import numpy as np


def decode_bounded_pcm(data, maximum_samples=16 * 16000):
    import av

    pieces, samples = [], 0
    resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)

    def append(frames):
        nonlocal samples
        for frame in frames:
            values = frame.to_ndarray().reshape(-1).astype(np.float32, copy=False)
            samples += len(values)
            if samples > maximum_samples:
                raise ValueError("Decoded recording exceeds the original duration bound.")
            pieces.append(values.copy())

    try:
        with av.open(io.BytesIO(data), mode="r", timeout=(15, 15)) as container:
            for frame in container.decode(audio=0):
                # A recorded container's timestamp offsets must not add waiting
                # samples; preserve the actual decoded audio, as ffmpeg did.
                frame.pts = None
                append(resampler.resample(frame))
            append(resampler.resample(None))
    except (av.error.FFmpegError, OSError) as error:
        raise ValueError("Could not read the recording. Please record again.") from error
    if not pieces:
        raise ValueError("Could not read the recording. Please record again.")
    return np.concatenate(pieces)
