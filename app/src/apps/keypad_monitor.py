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

from messaging import Publisher
from apps.message_topics import Topic, KeypadMessage
from apps.dtmf import DtmfPlayer

# ── GPIO config ───────────────────────────────────────────────────────────
ROW_PINS    = [16, 6, 13, 19]
COLUMN_PINS = [26, 20, 21]

KEY_MAP = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["*", "0", "#"],
]

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
    dtmf_player = DtmfPlayer()
    buffer = ""

    current_key: str | None = None  # key currently held down

    def handle_exit(sig, frame):
        dtmf_player.stop()
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
                dtmf_player.stop()

            # ── key pressed ──
            if key is not None:
                dtmf_player.play(key)

                if key == "#":
                    if buffer:
                        pub.send(KeypadMessage(year_entered=buffer))
                        print(f"Sent: year_entered={buffer!r}")
                        buffer = ""
                    else:
                        print("# pressed with empty buffer, ignoring.")
                elif key == "*":
                    print(f"Buffer cleared by '*' (was: {buffer!r})")
                    buffer = ""
                else:
                    buffer += key
                    print(f"Buffer: {buffer}")

            current_key = key

        time.sleep(0.02)

if __name__ == "__main__":
    main()
