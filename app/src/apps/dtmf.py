"""
dtmf.py — DTMF tone generation and playback.

Provides DtmfPlayer, which streams the correct two-frequency tone for a
keypad key while it is held, then stops cleanly on release.

Tone buffers are precomputed at import time — the audio callback does no
maths, it just copies the next chunk of a pre-built numpy array.
"""

import time
import math
import threading

import numpy as np
import sounddevice as sd

DTMF_FREQS: dict[str, tuple[int, int]] = {
    "1": (697, 1209), "2": (697, 1336), "3": (697, 1477),
    "4": (770, 1209), "5": (770, 1336), "6": (770, 1477),
    "7": (852, 1209), "8": (852, 1336), "9": (852, 1477),
    "*": (941, 1209), "0": (941, 1336), "#": (941, 1477),
}

_SAMPLE_RATE = 44100
_CHUNK_SIZE  = 1024   # frames per audio callback
_MIN_TONE_S  = 0.120  # minimum tone duration in seconds

# Number of chunks in each precomputed buffer — large enough to hold at
# least one full LCM cycle for every key, with no partial-chunk wrapping.
_BUFFER_CHUNKS = 64


def _precompute_buffers() -> dict[str, np.ndarray]:
    """
    Build a seamlessly-looping float32 buffer for each DTMF key.

    The buffer is an exact integer multiple of _CHUNK_SIZE samples so the
    callback always reads one aligned chunk with a simple index — no
    wraparound logic needed.
    """
    buf_len = _CHUNK_SIZE * _BUFFER_CHUNKS   # 65536 samples ≈ 1.5 s
    t = np.arange(buf_len) / _SAMPLE_RATE
    buffers = {}
    for key, (f1, f2) in DTMF_FREQS.items():
        buf = (np.sin(2 * np.pi * f1 * t) +
               np.sin(2 * np.pi * f2 * t)) * 0.3
        buffers[key] = buf.astype(np.float32)
    return buffers


# Built once at import time, shared across all DtmfPlayer instances
_BUFFERS: dict[str, np.ndarray] = _precompute_buffers()


class DtmfPlayer:
    """Streams a precomputed DTMF tone continuously while a key is held."""

    def __init__(self):
        self._stream: sd.OutputStream | None = None
        self._started_at = 0.0
        self._buf: np.ndarray | None = None
        self._pos = 0
        self._lock = threading.Lock()

    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            buf = self._buf
            pos = self._pos
            if buf is None:
                outdata[:, 0] = 0.0
                return
            outdata[:, 0] = buf[pos: pos + frames]
            self._pos = (pos + frames) % len(buf)

    def play(self, key: str) -> None:
        """Start streaming the precomputed DTMF tone for *key*."""
        self.stop()
        with self._lock:
            self._buf = _BUFFERS[key]
            self._pos = 0
        self._stream = sd.OutputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=_CHUNK_SIZE,
            callback=self._callback,
        )
        self._stream.start()
        self._started_at = time.monotonic()

    def stop(self) -> None:
        """Stop the tone, honouring the minimum duration."""
        if self._stream is not None:
            elapsed = time.monotonic() - self._started_at
            remaining = _MIN_TONE_S - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            with self._lock:
                self._buf = None
