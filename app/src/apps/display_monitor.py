#!/usr/bin/env python3
"""
display_monitor.py — Drives the screen.

Two sources drive the display:

  * PHONE_HOOK: when the handset is on-hook (hung up), blinks
    "< Pick Me Up!" once per half second. When lifted, stops blinking.

  * DISPLAY: any app can publish a DisplayMessage to show arbitrary text
    (newlines split it across lines) or clear the screen with blank text.
    This takes over from the blinking prompt.
"""

import os
import sys
import signal
import threading

from messaging import Subscriber
from devices.display import Display
from apps.message_topics import Topic, HookMessage, DisplayMessage

PICK_UP_TEXT = "\u2190 Pick Me Up!"   # left arrow + text
BLINK_HALF_PERIOD = 0.5               # seconds on / off -> 500ms on, 500ms off
TEXT_SIZE = 96


class DisplayController:
    """Blinks a prompt while on-hook; shows arbitrary text on request."""

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

    def _stop_blinking(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
            self._thread = None

    def stop_and_clear(self) -> None:
        """Stop the blink loop and clear the screen."""
        self._stop_blinking()
        self._display.clear()

    def show_text(self, text: str) -> None:
        """Stop blinking and show *text* (or clear the screen if blank)."""
        self._stop_blinking()
        if text:
            self._display.show_message(text, size=TEXT_SIZE)
        else:
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


def display_listener(controller: DisplayController) -> None:
    """Background thread: show text requested on the DISPLAY topic."""
    sub = Subscriber(Topic.DISPLAY, DisplayMessage)
    while True:
        _, msg = sub.receive()
        print(f"Display request: {msg.text!r}")
        controller.show_text(msg.text)


def main():
    display    = Display()
    controller = DisplayController(display)
    hook_sub   = Subscriber(Topic.PHONE_HOOK, HookMessage)

    thread = threading.Thread(target=display_listener, args=(controller,), daemon=True)
    thread.start()

    def handle_exit(sig, frame):
        # Best-effort cleanup, then force-exit so shutdown can't hang.
        try:
            controller.stop_and_clear()
            hook_sub.close()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Display monitor running... (Ctrl+C to stop)\n")

    # hook_monitor re-announces the current state periodically, so only act on
    # actual state changes. Otherwise the repeated "lifted" heartbeats would
    # keep clearing the screen and wipe any prompt shown via the DISPLAY topic.
    last_state = None
    while True:
        _, msg = hook_sub.receive()
        if msg.state == last_state:
            continue
        last_state = msg.state
        if msg.state == "hung_up":
            print("On-hook: blinking prompt.")
            controller.start_blinking()
        elif msg.state == "lifted":
            print("Off-hook: clearing screen.")
            controller.stop_and_clear()


if __name__ == "__main__":
    main()
