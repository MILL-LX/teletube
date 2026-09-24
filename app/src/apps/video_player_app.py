#!/usr/bin/env python3
"""
video_player_app.py — Listens for keypad year entries and plays a random video.

Subscribes to the KEYPAD topic and, on each KeypadMessage, picks a random
video file from the matching year subdirectory and plays it with mpv.

A background thread listens on the PHONE_HOOK topic and stops playback
when the handset is hung up.
"""

import os
import sys
import signal
import threading

from messaging import Subscriber
from apps.message_topics import Topic, KeypadMessage, HookMessage, PlaybackMessage
from devices.video_player import VideoPlayer
from devices.display import Display

HINT_SIZE = 50
HINT_COLOR = (0, 255, 0)   # bright green


def hint_text(year: str) -> str:
    return f"PRESS #\nfor another video\nfrom {year}"


def hook_listener(video_player: VideoPlayer) -> None:
    """Background thread: stop playback when the hook is hung up."""
    sub = Subscriber(Topic.PHONE_HOOK, HookMessage)
    while True:
        _, msg = sub.receive()
        if msg.state == "hung_up":
            print("Hook hung up, stopping playback.")
            video_player.stop()


def playback_listener(video_player: VideoPlayer, display: Display) -> None:
    """Background thread: show a hint on PLAYBACK 'hint' commands.

    Showing a hint stops the video (freeing the display) and draws the hint on
    the framebuffer, then resumes the video where it left off.
    """
    sub = Subscriber(Topic.PLAYBACK, PlaybackMessage)
    while True:
        _, msg = sub.receive()
        if msg.command == "hint":
            print("Showing hint.")
            text = hint_text(msg.text)
            video_player.interrupt_for_hint(
                show=lambda: display.show_message(text, fg=HINT_COLOR, size=HINT_SIZE),
                hide=display.clear,
                duration=msg.duration,
            )


def main():
    video_player = VideoPlayer()
    display = Display()
    sub = Subscriber(Topic.KEYPAD, KeypadMessage)

    threading.Thread(target=hook_listener, args=(video_player,), daemon=True).start()
    threading.Thread(target=playback_listener, args=(video_player, display), daemon=True).start()

    def handle_exit(sig, frame):
        # Best-effort cleanup (stop mpv), then force-exit so shutdown can't hang.
        try:
            video_player.stop()
            sub.close()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Video player app running... (Ctrl+C to stop)\n")

    while True:
        _, msg = sub.receive()
        year = msg.year_entered
        print(f"Received year: {year}")

        if not video_player.play_random_for_year(year):
            print(f"[WARN] No .mp4 files found for year {year}")


if __name__ == "__main__":
    main()
