#!/usr/bin/env python3
"""
display_monitor.py — Drives the screen based on the phone hook state.

When the handset is on-hook (hung up), blinks "< Pick Me Up!" once per
half second. When the handset is lifted, stops blinking and clears the
screen. Listens for HookMessages on the PHONE_HOOK topic.
"""

import sys
import signal
import threading

from messaging import Subscriber
from devices.display import Display
from apps.message_topics import Topic, HookMessage

PICK_UP_TEXT = "\u2190 Pick Me Up!"   # left arrow + text
BLINK_HALF_PERIOD = 0.5               # seconds on / off -> 500ms on, 500ms off
TEXT_SIZE = 96


class DisplayController:
    """Blinks a prompt while on-hook; clears the screen while off-hook."""

    def __init__(self, display: Display):
        self._display = display
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start_blinking(self) -> None:
        """Start the blink loop if not already running."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._blink_loop, daemon=True)
        self._thread.start()

    def stop_and_clear(self) -> None:
        """Stop the blink loop and clear the screen."""
        self._stop.set()
        if self._thread:
            self._thread.join()
            self._thread = None
        self._display.clear()

    def _blink_loop(self) -> None:
        showing = False
        while not self._stop.is_set():
            if showing:
                self._display.clear()
            else:
                self._display.show_message(PICK_UP_TEXT, size=TEXT_SIZE)
            showing = not showing
            self._stop.wait(timeout=BLINK_HALF_PERIOD)


def main():
    display    = Display()
    controller = DisplayController(display)
    sub        = Subscriber(Topic.PHONE_HOOK, HookMessage)

    def handle_exit(sig, frame):
        controller.stop_and_clear()
        sub.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Display monitor running... (Ctrl+C to stop)\n")

    while True:
        _, msg = sub.receive()
        if msg.state == "hung_up":
            print("On-hook: blinking prompt.")
            controller.start_blinking()
        elif msg.state == "lifted":
            print("Off-hook: clearing screen.")
            controller.stop_and_clear()


if __name__ == "__main__":
    main()
