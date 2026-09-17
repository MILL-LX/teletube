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

from pathlib import Path

DEFAULT_VIDEOS_DIR = Path("/home/pi/teletube-downloader/data/videos/ready")


class VideoPlayer:
    """Manages video playback from a year-organised directory."""

    def __init__(self, videos_dir: Path = DEFAULT_VIDEOS_DIR):
        self._videos_dir = Path(videos_dir)

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
