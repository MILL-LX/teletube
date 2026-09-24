#!/usr/bin/env python3
"""
ringer_monitor.py — Rings the phone when it has been left hung up.

Listens for hook state on the PHONE_HOOK topic. When the handset has been
hung up (on-hook) continuously for RING_DELAY seconds, it rings for up to
RING_DURATION seconds, stopping early as soon as the handset is lifted. If the
handset is still hung up after a ring, the delay countdown starts over.

At startup it begins counting the ring delay as though the handset had just
been hung up.
"""

import os
import sys
import time
import signal
import threading

from messaging import Subscriber
from devices.ringer import Ringer
from apps.message_topics import Topic, HookMessage

RING_DELAY = 300.0      # seconds hung up before ringing
RING_DURATION = 30.0   # max seconds to ring (stops early when lifted)
POLL_INTERVAL = 0.1    # seconds between state checks


class HookState:
    """Tracks the latest hook state from the PHONE_HOOK topic (thread-safe)."""

    def __init__(self):
        # Assume hung up at startup so the ring delay begins counting immediately.
        self._off_hook = False
        self._lock = threading.Lock()

    def set_off_hook(self, off_hook: bool) -> None:
        with self._lock:
            self._off_hook = off_hook

    def is_off_hook(self) -> bool:
        with self._lock:
            return self._off_hook


def hook_listener(state: HookState) -> None:
    """Background thread: keep HookState in sync with the PHONE_HOOK topic."""
    sub = Subscriber(Topic.PHONE_HOOK, HookMessage)
    while True:
        _, msg = sub.receive()
        state.set_off_hook(msg.state == "lifted")


def main():
    ringer = Ringer()
    state = HookState()

    def handle_exit(sig, frame):
        try:
            ringer.close()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    threading.Thread(target=hook_listener, args=(state,), daemon=True).start()

    print("Ringer monitor running... (Ctrl+C to stop)\n")

    while True:
        # Wait out the ring delay while the handset stays hung up. If it's
        # lifted at any point, restart the wait (only ring after a full
        # RING_DELAY of continuous on-hook time).
        hung_up_since = time.monotonic()
        while True:
            if state.is_off_hook():
                hung_up_since = None
            elif hung_up_since is None:
                hung_up_since = time.monotonic()   # just hung up; start counting
            elif time.monotonic() - hung_up_since >= RING_DELAY:
                break
            time.sleep(POLL_INTERVAL)

        # Ring until the handset is lifted or RING_DURATION elapses.
        print("Ringing.")
        ringer.start_ringing()
        ring_started = time.monotonic()
        while (not state.is_off_hook()
               and time.monotonic() - ring_started < RING_DURATION):
            time.sleep(POLL_INTERVAL)
        ringer.stop_ringing()
        print("Stopped ringing.")


if __name__ == "__main__":
    main()
