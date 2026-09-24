#!/usr/bin/env python3
"""
display_monitor.py — Drives the screen.

Two sources drive the display:

  * PHONE_HOOK: when the handset is on-hook (hung up), cycles between showing
    the title image steadily for 5 seconds and flashing the "< Pick Me Up!"
    prompt for 5 seconds. When lifted, stops and clears the screen.

  * DISPLAY: any app can publish a DisplayMessage to show arbitrary text
    (newlines split it across lines) or clear the screen with blank text.
    This takes over from the blinking prompt.
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path

from messaging import Subscriber
from devices.display import Display
from apps.message_topics import Topic, HookMessage, DisplayMessage

PICK_UP_TEXT = "\u2190 Pick Me Up!"   # left arrow + text
TEXT_SIZE = 96

IMAGE_PHASE = 5.0        # seconds the title image is shown, steady
FLASH_PHASE = 5.0        # seconds the "Pick Me Up!" prompt flashes
FLASH_HALF_PERIOD = 0.5  # seconds per flash frame (on/off) during the flash phase

# Repo-root assets/title_image.png (this file is app/src/apps/display_monitor.py).
TITLE_IMAGE = str(
    Path(__file__).resolve().parents[3] / "assets" / "title_image.png"
)


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

    def show_text(self, text: str, size: int | None = None) -> None:
        """Stop blinking and show *text* (or clear the screen if blank)."""
        self._stop_blinking()
        if text:
            self._display.show_message(text, size=size or TEXT_SIZE)
        else:
            self._display.clear()

    def _blink_loop(self) -> None:
        # Cycle: show the title image steadily for IMAGE_PHASE seconds,
        # then flash the "Pick Me Up!" prompt for FLASH_PHASE seconds.
        while not self._stop.is_set():
            # Image phase: show it once and hold for the whole phase.
            self._display.show_image(TITLE_IMAGE)
            if self._stop.wait(timeout=IMAGE_PHASE):
                break

            # Flash phase: toggle the prompt on/off until the phase elapses.
            phase_end = time.monotonic() + FLASH_PHASE
            showing = False
            while not self._stop.is_set() and time.monotonic() < phase_end:
                if showing:
                    self._display.clear()
                else:
                    self._display.show_message(PICK_UP_TEXT, size=TEXT_SIZE)
                showing = not showing
                self._stop.wait(timeout=FLASH_HALF_PERIOD)


def display_listener(controller: DisplayController) -> None:
    """Background thread: show text requested on the DISPLAY topic."""
    sub = Subscriber(Topic.DISPLAY, DisplayMessage)
    while True:
        _, msg = sub.receive()
        print(f"Display request: {msg.text!r} (size={msg.size})")
        controller.show_text(msg.text, msg.size)


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
