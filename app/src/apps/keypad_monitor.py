#!/usr/bin/env python3
"""
keypad_monitor.py — Reads the 4x3 keypad and publishes year entries.

Uses a state machine with two states:
  - ignoring_keypad: default; keypad is not scanned (hook is on-hook)
  - monitoring_keypad: keypad is actively scanned (hook is off-hook)

Transitions are driven by PhoneHookMessages received on the PHONE_HOOK topic.
While monitoring, digit keys accumulate in a buffer. # sends the buffer as a
KeypadMessage and * clears it. DTMF tones play while keys are held.
"""

import sys
import time
import signal
import threading

from statemachine import StateMachine, State

from messaging import Publisher, Subscriber
from apps.message_topics import Topic, KeypadMessage, PhoneHookMessage
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

# ── State machine ─────────────────────────────────────────────────────────
class KeypadStateMachine(StateMachine):
    """Manages whether the keypad is actively monitored."""

    ignoring_keypad  = State(initial=True)
    monitoring_keypad = State()

    hook_lifted = ignoring_keypad.to(monitoring_keypad)
    hook_hung_up = monitoring_keypad.to(ignoring_keypad)

    def __init__(self, pub: Publisher, dtmf_player: DtmfPlayer):
        self._pub = pub
        self._dtmf_player = dtmf_player
        self._buffer = ""
        self._current_key: str | None = None
        super().__init__()

    def on_enter_ignoring_keypad(self):
        """Clear state when the hook is hung up."""
        self._dtmf_player.stop()
        self._buffer = ""
        self._current_key = None
        print("Ignoring keypad.")

    def on_enter_monitoring_keypad(self):
        print("Monitoring keypad.")

    def process_key(self, lgpio, h) -> None:
        """Scan the keypad and act on press/release. Call only while monitoring."""
        key = scan_keypad(lgpio, h)

        if key != self._current_key:
            if self._current_key is not None:
                self._dtmf_player.stop()

            if key is not None:
                self._dtmf_player.play(key)

                if key == "#":
                    if self._buffer:
                        self._pub.send(KeypadMessage(year_entered=self._buffer))
                        print(f"Sent: year_entered={self._buffer!r}")
                        self._buffer = ""
                    else:
                        print("# pressed with empty buffer, ignoring.")
                elif key == "*":
                    print(f"Buffer cleared (was: {self._buffer!r})")
                    self._buffer = ""
                else:
                    self._buffer += key
                    print(f"Buffer: {self._buffer}")

            self._current_key = key

# ── Hook listener ─────────────────────────────────────────────────────────
def hook_listener(sm: KeypadStateMachine) -> None:
    """Background thread: receives PhoneHookMessages and drives transitions."""
    sub = Subscriber(Topic.PHONE_HOOK, PhoneHookMessage)
    while True:
        _, msg = sub.receive()
        if msg.state == "lifted" and sm.monitoring_keypad not in sm.configuration:
            sm.hook_lifted()
        elif msg.state == "hung_up" and sm.monitoring_keypad in sm.configuration:
            sm.hook_hung_up()

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    lgpio, h = init_gpio()
    pub         = Publisher(Topic.KEYPAD)
    dtmf_player = DtmfPlayer()
    sm          = KeypadStateMachine(pub, dtmf_player)

    thread = threading.Thread(target=hook_listener, args=(sm,), daemon=True)
    thread.start()

    def handle_exit(sig, frame):
        dtmf_player.stop()
        pub.close()
        cleanup_gpio(lgpio, h)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Keypad monitor running... (Ctrl+C to stop)")
    print("Waiting for hook to be lifted.\n")

    while True:
        if sm.monitoring_keypad in sm.configuration:
            sm.process_key(lgpio, h)
        time.sleep(0.02)

if __name__ == "__main__":
    main()
