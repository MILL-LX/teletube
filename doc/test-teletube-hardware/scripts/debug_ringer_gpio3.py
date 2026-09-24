#!/usr/bin/env python3
"""
debug_ringer_gpio3.py — Monitor GPIO3 (ringer enable) without driving it.

Claims GPIO3 as an input and prints its level once a second until interrupted.
Does not drive the pin.

Run:
    python3 debug_ringer_gpio3.py

Press Ctrl+C to exit.
"""

import sys
import time
import signal

GPIO_PIN = 3
POLL_INTERVAL = 1.0  # seconds between reads


def main():
    try:
        import lgpio
    except ImportError:
        print("[ERROR] lgpio not installed (try: sudo apt install python3-lgpio).")
        sys.exit(1)

    handle = lgpio.gpiochip_open(0)
    if handle < 0:
        print("[ERROR] Could not open GPIO chip.")
        sys.exit(1)

    # Claim GPIO3 as an input (read-only; the pin is not driven).
    lgpio.gpio_claim_input(handle, GPIO_PIN)
    print(f"[OK] Monitoring GPIO{GPIO_PIN} every {POLL_INTERVAL:g}s. "
          "Press Ctrl+C to exit.")

    def cleanup(sig=None, frame=None):
        try:
            lgpio.gpiochip_close(handle)
            print(f"\n[OK] GPIO{GPIO_PIN} released.")
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Read and report the pin level every second.
    while True:
        level = lgpio.gpio_read(handle, GPIO_PIN)
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] GPIO{GPIO_PIN} = {level} ({'HIGH' if level else 'LOW'})")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
