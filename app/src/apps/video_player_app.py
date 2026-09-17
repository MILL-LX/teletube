#!/usr/bin/env python3
"""
video_player_app.py — Listens for keypad year entries and plays a random video.

Subscribes to the KEYPAD topic and, on each KeypadMessage, picks a random
video file from the matching year subdirectory and plays it with mpv.
"""

import sys
import random
import signal
import subprocess

from messaging import Subscriber
from apps.message_topics import Topic, KeypadMessage
from devices.video_player import VideoPlayer

MPV_COMMAND = ["mpv", "--drm-connector=DSI-1", "--video-rotate=270"]


def play(path: str) -> None:
    """Play *path* with mpv, blocking until playback finishes."""
    subprocess.run(MPV_COMMAND + [path], check=True)


def main():
    video_player = VideoPlayer()
    sub = Subscriber(Topic.KEYPAD, KeypadMessage)

    def handle_exit(sig, frame):
        sub.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Video player app running... (Ctrl+C to stop)\n")

    while True:
        _, msg = sub.receive()
        year = msg.year_entered
        print(f"Received year: {year}")

        videos = video_player.videos_for_year(year)
        if not videos:
            print(f"[WARN] No .mp4 files found for year {year}")
            continue

        chosen = random.choice(videos)
        print(f"Playing: {chosen}")
        play(str(chosen))


if __name__ == "__main__":
    main()
