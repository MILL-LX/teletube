#!/usr/bin/env python3
"""
keypad_monitor.py — Reads the 4x3 keypad and publishes year entries.

While a key is held, plays its DTMF tone continuously.
Tone stops on release.

Collects digit keys until # is pressed, then publishes a KeypadMessage
with the collected digits as year_entered on the KEYPAD topic.
* clears the current buffer without publishing.
"""

import sys
import time
import signal
import threading

import numpy as np
import sounddevice as sd

from messaging import Publisher
from apps.message_topics import Topic, KeypadMessage

# ── GPIO config ───────────────────────────────────────────────────────────
ROW_PINS    = [16, 6, 13, 19]
COLUMN_PINS = [26, 20, 21]

KEY_MAP = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["*", "0", "#"],
]

DTMF_FREQS = {
    "1": (697, 1209), "2": (697, 1336), "3": (697, 1477),
    "4": (770, 1209), "5": (770, 1336), "6": (770, 1477),
    "7": (852, 1209), "8": (852, 1336), "9": (852, 1477),
    "*": (941, 1209), "0": (941, 1336), "#": (941, 1477),
}

SAMPLE_RATE = 44100
CHUNK_SIZE  = 1024   # frames per callback

# ── DTMF tone player ──────────────────────────────────────────────────────

class DtmfPlayer:
    """Streams a DTMF tone continuously while a key is held."""

    def __init__(self):
        self._stream: sd.OutputStream | None = None
        self._phase = 0.0
        self._f1 = 0.0
        self._f2 = 0.0
        self._lock = threading.Lock()

    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            t = (self._phase + np.arange(frames)) / SAMPLE_RATE
            tone = (np.sin(2 * np.pi * self._f1 * t) +
                    np.sin(2 * np.pi * self._f2 * t)) * 0.3
            self._phase = (self._phase + frames) % SAMPLE_RATE
        outdata[:, 0] = tone

    def play(self, key: str) -> None:
        """Start streaming the DTMF tone for *key*."""
        self.stop()
        f1, f2 = DTMF_FREQS[key]
        with self._lock:
            self._f1 = f1
            self._f2 = f2
            self._phase = 0.0
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop any currently playing tone."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

# ── GPIO ──────────────────────────────────────────────────────────────────
def init_gpio():
    try:
        import lgpio
        h = lgpio.gpiochip_open(0)
        if h < 0:
            print("[ERROR] Could not open GPIO chip.")
            sys.exit(1)
        for row in ROW_PINS:
            lgpio.gpio_claim_output(h, row, 0)
        for col in COLUMN_PINS:
            lgpio.gpio_claim_input(h, col, lgpio.SET_PULL_DOWN)
        print(f"[OK] GPIO ready. Rows: {ROW_PINS}  Cols: {COLUMN_PINS}")
        return lgpio, h
    except ImportError:
        print("[ERROR] lgpio not installed.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

def cleanup_gpio(lgpio, h):
    try:
        for row in ROW_PINS:
            lgpio.gpio_write(h, row, 0)
        lgpio.gpiochip_close(h)
        print("[OK] GPIO released.")
    except Exception:
        pass

def scan_keypad(lgpio, h) -> str | None:
    """Return the key that is currently pressed, or None."""
    for i, row in enumerate(ROW_PINS):
        for r in ROW_PINS:
            lgpio.gpio_write(h, r, 1 if r == row else 0)
        time.sleep(0.005)
        for j, col in enumerate(COLUMN_PINS):
            if lgpio.gpio_read(h, col):
                return KEY_MAP[i][j]
    return None

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    lgpio, h = init_gpio()
    pub    = Publisher(Topic.KEYPAD)
    player = DtmfPlayer()
    buffer = ""

    current_key: str | None = None  # key currently held down

    def handle_exit(sig, frame):
        player.stop()
        pub.close()
        cleanup_gpio(lgpio, h)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Keypad monitor running... (Ctrl+C to stop)")
    print("Enter digits and press # to send, * to clear.\n")

    while True:
        key = scan_keypad(lgpio, h)

        if key != current_key:
            # ── key released ──
            if current_key is not None:
                player.stop()

            # ── key pressed ──
            if key is not None:
                player.play(key)

                if key == "#":
                    if buffer:
                        pub.send(KeypadMessage(year_entered=buffer))
                        print(f"Sent: year_entered={buffer!r}")
                        buffer = ""
                    else:
                        print("# pressed with empty buffer, ignoring.")
                elif key == "*":
                    print(f"Buffer cleared (was: {buffer!r})")
                    buffer = ""
                else:
                    buffer += key
                    print(f"Buffer: {buffer}")

            current_key = key

        time.sleep(0.02)

if __name__ == "__main__":
    main()
