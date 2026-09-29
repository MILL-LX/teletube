#!/usr/bin/env python3
"""
video_player_app.py — Plays videos for the year entered on the keypad.

Subscribes to KEYPAD (year selections) and PHONE_HOOK (handset state). A
dedicated play-loop thread plays videos for the selected year: when a video
finishes on its own it plays another random one from the same year, continuing
while the handset is off the hook. Pressing a new year (or #) switches to a
fresh random video from that year; hanging up stops playback.

PLAYBACK 'hint' messages briefly show a hint over the current video.
"""

import os
import sys
import signal
import threading

from messaging import Subscriber
from apps.message_topics import Topic, KeypadMessage, HookMessage, PlaybackMessage
from devices.video_player import VideoPlayer, PlayResult
from devices.display import Display

HINT_SIZE = 50
HINT_COLOR = (0, 255, 0)   # bright green
YEAR_SIZE = 96             # match the year size shown during entry (display_monitor)


def hint_text(year: str) -> str:
    return f"PRESS #\nfor another video\nfrom {year}"


class Controller:
    """Coordinates the play loop with keypad and hook events."""

    def __init__(self, video_player: VideoPlayer):
        self._video_player = video_player
        self._lock = threading.Lock()
        self._off_hook = False
        self._year: str | None = None       # year to play (None = nothing)
        self._wake = threading.Event()       # signals the play loop to (re)evaluate

    # ── event inputs ───────────────────────────────────────────────────

    def set_year(self, year: str) -> None:
        """Request playback of *year* (a keypad selection or # advance)."""
        with self._lock:
            self._year = year
        self._video_player.stop()   # interrupt any current video; play loop restarts
        self._wake.set()

    def set_off_hook(self, off_hook: bool) -> None:
        """Update handset state. Hanging up stops playback."""
        with self._lock:
            self._off_hook = off_hook
            if not off_hook:
                self._year = None
        if not off_hook:
            self._video_player.stop()
        self._wake.set()

    # ── play loop ──────────────────────────────────────────────────────

    def run(self) -> None:
        """Play the selected year's videos, advancing while off the hook."""
        while True:
            self._wake.clear()
            with self._lock:
                year = self._year if self._off_hook else None
            if year is None:
                self._wake.wait()
                continue

            result = self._video_player.play_random_for_year(year)

            if result == PlayResult.NO_VIDEOS:
                print(f"[WARN] No videos for year {year}")
                with self._lock:
                    if self._year == year:
                        self._year = None   # nothing to play; wait for a new year
            # COMPLETED  -> loop; if still off-hook and same year, plays another.
            # INTERRUPTED -> loop; a new year or hang-up already updated state.


def hook_listener(controller: Controller) -> None:
    sub = Subscriber(Topic.PHONE_HOOK, HookMessage)
    while True:
        _, msg = sub.receive()
        controller.set_off_hook(msg.state == "lifted")


def keypad_listener(controller: Controller) -> None:
    sub = Subscriber(Topic.KEYPAD, KeypadMessage)
    while True:
        _, msg = sub.receive()
        print(f"Received year: {msg.year_entered}")
        controller.set_year(msg.year_entered)


def playback_listener(video_player: VideoPlayer, display: Display) -> None:
    """Show a hint over the current video on PLAYBACK 'hint' commands."""
    sub = Subscriber(Topic.PLAYBACK, PlaybackMessage)
    while True:
        _, msg = sub.receive()
        if msg.command == "hint":
            print("Showing hint.")
            year = msg.text
            video_player.interrupt_for_hint(
                show=lambda: display.show_message(
                    hint_text(year), fg=HINT_COLOR, size=HINT_SIZE
                ),
                # When the hint ends, redraw the year (what was shown before the
                # video started) so it briefly appears before the video resumes.
                # Use the same size the year is drawn at during entry.
                hide=lambda: display.show_message(year, size=YEAR_SIZE),
                duration=msg.duration,
            )


def main():
    video_player = VideoPlayer()
    display = Display()
    controller = Controller(video_player)

    threading.Thread(target=hook_listener, args=(controller,), daemon=True).start()
    threading.Thread(target=keypad_listener, args=(controller,), daemon=True).start()
    threading.Thread(target=playback_listener, args=(video_player, display), daemon=True).start()

    def handle_exit(sig, frame):
        try:
            video_player.stop()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Video player app running... (Ctrl+C to stop)\n")
    controller.run()


if __name__ == "__main__":
    main()
