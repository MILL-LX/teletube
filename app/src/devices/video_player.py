"""
video_player.py — Plays videos from a year-organised directory tree.

Expected directory layout:
    <videos_dir>/
        2007/
            some_video.mp4
            ...
        2008/
            ...

play_random_for_year() blocks until the chosen video finishes and returns a
PlayResult describing the outcome. The caller decides whether to play another
(e.g. keep going while the phone is off the hook). A hint interruption is
transparent: the same video is stopped, the hint is shown, then the video
resumes where it left off — the call only returns once the video truly ends,
is stopped, or has no videos to play.
"""

import json
import time
import enum
import socket
import random
import threading
import subprocess
from pathlib import Path

DEFAULT_VIDEOS_DIR = Path("/home/pi/teletube-downloader/data/videos/ready")
_IPC_SOCKET = "/tmp/teletube-mpv.sock"
MPV_COMMAND = [
    "mpv",
    "--drm-connector=DSI-1",
    "--video-rotate=270",
    f"--input-ipc-server={_IPC_SOCKET}",
]


class PlayResult(enum.Enum):
    """Outcome of play_random_for_year()."""
    NO_VIDEOS = "no_videos"    # the year has no videos to play
    COMPLETED = "completed"    # the video played to the end
    INTERRUPTED = "interrupted"  # playback was stopped or superseded


class VideoPlayer:
    """Plays one video at a time from a year-organised directory."""

    def __init__(self, videos_dir: Path = DEFAULT_VIDEOS_DIR):
        self._videos_dir = Path(videos_dir)
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._generation = 0          # bumped by stop() to interrupt a play
        self._start_at = 0.0          # resume offset set by a hint interruption
        self._resume_after = 0.0      # monotonic time to hold before resuming
        self._interrupt = threading.Event()  # set by stop() to break the hint-resume wait

    # ── Library queries ────────────────────────────────────────────────

    def year_range(self) -> tuple[str, str] | None:
        """Return (min_year, max_year) as strings from numeric subdirectory names."""
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

    def has_videos_for_year(self, year: str) -> bool:
        """Return True if there is at least one video for *year*."""
        return bool(self.videos_for_year(year))

    # ── Playback ───────────────────────────────────────────────────────

    def play_random_for_year(self, year: str) -> PlayResult:
        """Play a random video from *year*, blocking until it ends.

        Returns:
          NO_VIDEOS   — the year has no videos.
          COMPLETED   — the video played to the end on its own.
          INTERRUPTED — playback was stopped (stop()) or superseded by another
                        play_random_for_year() call.

        A hint interruption (see interrupt_for_hint) is transparent: the video
        is stopped, the hint shown, then the same video resumes from its saved
        position, and this call keeps blocking until the video truly ends.
        """
        videos = self.videos_for_year(year)
        if not videos:
            return PlayResult.NO_VIDEOS

        video = random.choice(videos)
        with self._lock:
            self._generation += 1
            gen = self._generation
            self._start_at = 0.0
            self._interrupt.clear()   # fresh play; not interrupted yet
            old_proc = self._process
        # Supersede any currently-playing video.
        if old_proc is not None and old_proc.poll() is None:
            old_proc.terminate()

        print(f"Playing: {video}")

        while True:
            with self._lock:
                if gen != self._generation:
                    return PlayResult.INTERRUPTED
                start_at = self._start_at
                self._start_at = 0.0          # consume the resume offset
                cmd = list(MPV_COMMAND)
                if start_at > 0:
                    cmd.append(f"--start=+{start_at}")
                cmd.append(str(video))
                proc = subprocess.Popen(cmd)
                self._process = proc

            proc.wait()

            with self._lock:
                if self._process is proc:
                    self._process = None
                # Superseded (stop() or a new play) while mpv was running.
                if gen != self._generation:
                    return PlayResult.INTERRUPTED
                # A hint interruption set a resume point: relaunch the same
                # video after the hint window.
                if self._start_at > 0:
                    resume_after = self._resume_after
                else:
                    return PlayResult.COMPLETED

            delay = resume_after - time.monotonic()
            if delay > 0:
                # Interruptible wait: stop() sets _interrupt so an advance /
                # hang-up during the hint window doesn't have to wait it out.
                if self._interrupt.wait(timeout=delay):
                    return PlayResult.INTERRUPTED
            # Loop to relaunch the same video at the saved offset.

    def stop(self) -> None:
        """Stop playback, causing an in-progress play_random_for_year() to
        return INTERRUPTED."""
        with self._lock:
            self._generation += 1
            self._start_at = 0.0
            proc = self._process
        self._interrupt.set()   # break any hint-resume wait in progress
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def interrupt_for_hint(self, show, hide=None, duration: float = 3.0) -> None:
        """Briefly interrupt the current video to show a hint, then resume it.

        *show* is a zero-arg callable that displays the hint (e.g. on the
        framebuffer). *hide*, if given, is called when the hint window ends to
        clear it before the video repaints. mpv is stopped so it releases the
        DRM plane and the hint is visible; the in-progress play_random_for_year
        relaunches the same video from its saved position once the hint window
        elapses. Runs on its own thread; returns immediately.
        """
        threading.Thread(
            target=self._interrupt_for_hint, args=(show, hide, duration), daemon=True
        ).start()

    def _interrupt_for_hint(self, show, hide, duration: float) -> None:
        with self._lock:
            gen = self._generation
            playing = self._process is not None and self._process.poll() is None
        if not playing:
            return

        pos = self._time_pos() or 0.0

        with self._lock:
            if gen != self._generation:
                return
            self._start_at = pos                             # relaunch offset
            self._resume_after = time.monotonic() + duration  # hold relaunch until then
            proc = self._process
        # Stopping mpv makes the play loop's proc.wait() return; because
        # _start_at > 0 and the generation is unchanged, it relaunches the same
        # video at the offset — but only after _resume_after.
        if proc is not None and proc.poll() is None:
            proc.terminate()

        try:
            show()
        except Exception as e:
            print(f"[WARN] hint show() failed: {e}")

        # Hold the hint for its window, but end early if the play is superseded
        # (e.g. the user pressed # to advance). Either way, run hide() when the
        # hint ends so the year is redrawn before the video (resumed or new)
        # repaints over it.
        self._interrupt.wait(timeout=duration)
        if hide is not None:
            try:
                hide()
            except Exception as e:
                print(f"[WARN] hint hide() failed: {e}")

    def _time_pos(self) -> float | None:
        """Query mpv's current playback position in seconds, or None."""
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                sock.connect(_IPC_SOCKET)
                sock.sendall(
                    (json.dumps({"command": ["get_property", "time-pos"]}) + "\n").encode()
                )
                data = sock.recv(4096).decode()
                sock.shutdown(socket.SHUT_WR)
            for line in data.splitlines():
                obj = json.loads(line)
                if obj.get("error") == "success" and "data" in obj:
                    return float(obj["data"])
        except (OSError, ValueError, KeyError):
            pass
        return None
