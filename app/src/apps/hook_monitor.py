#!/usr/bin/env python3
"""
hook_monitor.py — Monitors the telephone hook switch and publishes state changes.

Publishes a PhoneHookMessage to the PHONE_HOOK topic whenever the handset
is lifted ("lifted") or hung up ("hung_up").
"""

import sys
import time
import signal

from messaging import Publisher
from apps.hook import Hook
from apps.message_topics import Topic, PhoneHookMessage

POLL_INTERVAL = 0.05  # seconds between reads


def main():
    hook = Hook()
    pub  = Publisher(Topic.PHONE_HOOK)

    # Publish the initial state immediately at startup
    last_state = hook.is_off_hook()
    event = "lifted" if last_state else "hung_up"
    pub.send(PhoneHookMessage(state=event))
    print(f"Initial hook state: {event}")

    def handle_exit(sig, frame):
        pub.close()
        hook.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Hook monitor running... (Ctrl+C to stop)\n")

    while True:
        state = hook.is_off_hook()
        if state != last_state:
            event = "lifted" if state else "hung_up"
            pub.send(PhoneHookMessage(state=event))
            print(f"Hook {event}")
            last_state = state
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
