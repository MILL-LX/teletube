#!/usr/bin/env python3
"""
video_player_app.py — Listens for keypad year entries and plays a random video.

Subscribes to the KEYPAD topic and, on each KeypadMessage, picks a random
video file from the matching year subdirectory and plays it with mpv.

A background thread listens on the PHONE_HOOK topic and stops playback
when the handset is hung up.
"""

import sys
import signal
import threading

from messaging import Subscriber
from apps.message_topics import Topic, KeypadMessage, HookMessage
from devices.video_player import VideoPlayer


def hook_listener(video_player: VideoPlayer) -> None:
    """Background thread: stop playback when the hook is hung up."""
    sub = Subscriber(Topic.PHONE_HOOK, HookMessage)
    while True:
        _, msg = sub.receive()
        if msg.state == "hung_up":
            print("Hook hung up, stopping playback.")
            video_player.stop()


def main():
    video_player = VideoPlayer()
    sub = Subscriber(Topic.KEYPAD, KeypadMessage)

    thread = threading.Thread(target=hook_listener, args=(video_player,), daemon=True)
    thread.start()

    def handle_exit(sig, frame):
        video_player.stop()
        sub.close()
        sys.exit(0)
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
