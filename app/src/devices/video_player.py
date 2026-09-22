"""
video_player.py — Plays videos from a year-organised directory tree.

Expected directory layout:
    <videos_dir>/
        2007/
            some_video.mp4
            ...
        2008/
            ...
"""

import random
import threading
import subprocess
from pathlib import Path

DEFAULT_VIDEOS_DIR = Path("/home/pi/teletube-downloader/data/videos/ready")
MPV_COMMAND = ["mpv", "--drm-connector=DSI-1", "--video-rotate=270"]


class VideoPlayer:
    """Manages video playback from a year-organised directory."""

    def __init__(self, videos_dir: Path = DEFAULT_VIDEOS_DIR):
        self._videos_dir = Path(videos_dir)
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def year_range(self) -> tuple[str, str] | None:
        """Return (min_year, max_year) as strings based on numeric subdirectory names.

        Returns None if no valid year directories are found.
        """
        years = [
            p.name
            for p in self._videos_dir.iterdir()
            if p.is_dir() and p.name.isdigit() and len(p.name) == 4
        ]
        if not years:
            return None
        return min(years), max(years)

    def videos_for_year(self, year: str) -> list[Path]:
        """Return all .mp4 files in the subdirectory for *year*."""
        year_dir = self._videos_dir / year
        if not year_dir.is_dir():
            return []
        return list(year_dir.glob("*.mp4"))

    def play_random_for_year(self, year: str) -> bool:
        """Play a random video from *year*, blocking until it finishes or is stopped.

        Returns False if no videos are available for the year, True otherwise.
        """
        videos = self.videos_for_year(year)
        if not videos:
            return False

        chosen = random.choice(videos)
        print(f"Playing: {chosen}")

        self.stop()  # stop anything already playing
        with self._lock:
            self._process = subprocess.Popen(MPV_COMMAND + [str(chosen)])
        proc = self._process

        proc.wait()
        with self._lock:
            if self._process is proc:
                self._process = None
        return True

    def stop(self) -> None:
        """Stop the currently playing video, if any."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()
