"""
video_player.py — Plays videos from a year-organised directory tree.

Expected directory layout:
    <videos_dir>/
        2007/
            some_video.mp4
            ...
        2008/
            ...

Playback runs in a background thread owned by VideoPlayer. A video plays until
it finishes, is stopped, or is interrupted to show a hint. Showing a hint stops
mpv (releasing the DRM display plane so a framebuffer message is visible), then
restarts the same video from where it left off.
"""

import json
import time
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


class VideoPlayer:
    """Manages video playback from a year-organised directory."""

    def __init__(self, videos_dir: Path = DEFAULT_VIDEOS_DIR):
        self._videos_dir = Path(videos_dir)
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        # Current playback intent, guarded by _lock:
        self._current_video: Path | None = None  # file being played
        self._start_at = 0.0                      # offset to (re)start at
        self._resume_after = 0.0                  # monotonic time before which not to relaunch
        self._generation = 0                      # bumped to cancel a play

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

    def play_random_for_year(self, year: str) -> bool:
        """Start playing a random video from *year*.

        Non-blocking: playback runs on a background thread, so a subsequent
        call (e.g. the user pressing # to advance) immediately supersedes the
        current video. Returns False if no videos are available, True otherwise.
        """
        videos = self.videos_for_year(year)
        if not videos:
            return False

        chosen = random.choice(videos)
        with self._lock:
            self._generation += 1
            gen = self._generation
            self._current_video = chosen
            self._start_at = 0.0
            proc = self._process
        # Stop any video currently playing so _run for the new generation takes over.
        if proc is not None and proc.poll() is None:
            proc.terminate()
        print(f"Playing: {chosen}")
        threading.Thread(target=self._run, args=(gen,), daemon=True).start()
        return True

    def _run(self, gen: int) -> None:
        """Run mpv for the current video until it ends or this play is cancelled.

        If interrupted for a hint, mpv exits but the video is relaunched from the
        saved offset (same generation). A stop()/new video bumps the generation
        and ends the loop.
        """
        while True:
            with self._lock:
                if gen != self._generation or self._current_video is None:
                    return
                video = self._current_video
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
                # Only clear the shared handle if it's still ours (a newer
                # generation may have already replaced it).
                if self._process is proc:
                    self._process = None
                # If this play was superseded (stop / new video), exit without
                # touching the newer generation's state.
                if gen != self._generation:
                    return
                # If a hint interruption set a new resume point, relaunch — but
                # only after the hint window, so the framebuffer hint stays
                # visible (mpv would otherwise reclaim the display immediately).
                if self._start_at > 0:
                    resume_after = self._resume_after
                else:
                    # Video ended naturally.
                    self._current_video = None
                    return

            # Wait out the hint window (outside the lock) before relaunching.
            delay = resume_after - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            # Loop to relaunch at the saved offset.

    def stop(self) -> None:
        """Stop playback entirely and cancel any pending relaunch."""
        with self._lock:
            self._generation += 1
            self._current_video = None
            self._start_at = 0.0
            proc = self._process
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def interrupt_for_hint(self, show, hide=None, duration: float = 3.0) -> None:
        """Stop the video, call show(), and resume where it left off after *duration*.

        *show* is a zero-arg callable that displays the hint (e.g. on the
        framebuffer). *hide*, if given, is a zero-arg callable invoked when the
        hint window ends, to clear the hint before the video repaints — this
        stops the hint lingering in the framebuffer where it could flash back
        during a later video swap. mpv is stopped first so it releases the DRM
        plane and the hint is visible; the video is relaunched from its saved
        position once the hint window elapses. If the video was stopped or
        changed during the hint, no resume happens. Runs on its own thread;
        returns immediately.
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
            # Only interrupt if still the same play.
            if gen != self._generation:
                return
            self._start_at = pos                               # relaunch offset
            self._resume_after = time.monotonic() + duration   # hold relaunch until then
            proc = self._process
        # Stopping mpv makes _run's proc.wait() return; because _start_at > 0
        # and the generation is unchanged, _run relaunches at the offset — but
        # only after _resume_after, keeping the hint on screen for the duration.
        if proc is not None and proc.poll() is None:
            proc.terminate()

        try:
            show()
        except Exception as e:
            print(f"[WARN] hint show() failed: {e}")

        # Hold the hint for its window, then clear it so it doesn't linger in
        # the framebuffer. mpv repaints when _run relaunches just after this.
        time.sleep(duration)
        # Skip the clear if this play was superseded meanwhile (e.g. the user
        # pressed # to advance): the new video owns the screen now, and clearing
        # would flash black over it.
        with self._lock:
            superseded = gen != self._generation
        if hide is not None and not superseded:
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
