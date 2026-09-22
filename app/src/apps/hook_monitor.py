#!/usr/bin/env python3
"""
hook_monitor.py — Monitors the telephone hook switch and publishes state changes.

Publishes a HookMessage to the PHONE_HOOK topic whenever the handset
is lifted ("lifted") or hung up ("hung_up").
"""

import os
import sys
import time
import signal

from messaging import Publisher
from devices.hook import Hook
from apps.message_topics import Topic, HookMessage

POLL_INTERVAL = 0.05    # seconds between hook reads
HEARTBEAT_INTERVAL = 1.0  # seconds between re-announcements of the current state


def _state_name(off_hook: bool) -> str:
    return "lifted" if off_hook else "hung_up"


def main():
    hook = Hook()
    pub  = Publisher(Topic.PHONE_HOOK)

    def handle_exit(sig, frame):
        # Best-effort cleanup, then force-exit so nothing can hold up shutdown.
        try:
            pub.close()
            hook.close()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Hook monitor running... (Ctrl+C to stop)\n")

    # Publish the current state on every change AND re-announce it periodically.
    # The heartbeat lets consumers that started after us (and missed an earlier
    # broadcast, due to ZeroMQ's slow-joiner behaviour) catch up on the current
    # state. Consumers already ignore redundant same-state messages.
    last_state = hook.is_off_hook()
    pub.send(HookMessage(state=_state_name(last_state)))
    print(f"Initial hook state: {_state_name(last_state)}")
    last_announce = time.monotonic()

    while True:
        state = hook.is_off_hook()
        now = time.monotonic()

        if state != last_state:
            event = _state_name(state)
            pub.send(HookMessage(state=event))
            print(f"Hook {event}")
            last_state = state
            last_announce = now
        elif now - last_announce >= HEARTBEAT_INTERVAL:
            pub.send(HookMessage(state=_state_name(state)))
            last_announce = now

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
