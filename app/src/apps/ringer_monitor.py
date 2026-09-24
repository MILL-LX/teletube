#!/usr/bin/env python3
"""
ringer_monitor.py — Exercises the ringer.

Rings for 15 seconds, then stays silent for 15 seconds, repeating. The ringer
itself handles the ring cadence (warble/on-off pattern) while active.
"""

import os
import sys
import time
import signal

from devices.ringer import Ringer

RING_DURATION = 15.0    # seconds the ringer sounds each cycle
SILENT_DURATION = 15.0  # seconds of silence between rings


def main():
    ringer = Ringer()

    def handle_exit(sig, frame):
        try:
            ringer.close()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Ringer monitor running... (Ctrl+C to stop)\n")

    while True:
        print("Ring start.")
        ringer.start_ringing()
        time.sleep(RING_DURATION)

        print("Ring stop.")
        ringer.stop_ringing()
        time.sleep(SILENT_DURATION)


if __name__ == "__main__":
    main()
