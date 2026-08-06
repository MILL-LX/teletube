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
from apps.message_topics import Topic, PhoneHookMessage

# ── GPIO config ───────────────────────────────────────────────────────────
OFF_HOOK_PIN  = 12
POLL_INTERVAL = 0.05  # seconds between reads

# ── GPIO ──────────────────────────────────────────────────────────────────
def init_gpio():
    try:
        import lgpio
        h = lgpio.gpiochip_open(0)
        if h < 0:
            print("[ERROR] Could not open GPIO chip.")
            sys.exit(1)
        lgpio.gpio_claim_input(h, OFF_HOOK_PIN, lgpio.SET_PULL_UP)
        print(f"[OK] GPIO {OFF_HOOK_PIN} ready with pull-up.")
        return lgpio, h
    except ImportError:
        print("[ERROR] lgpio not installed.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

def cleanup_gpio(lgpio, h):
    try:
        lgpio.gpiochip_close(h)
        print("[OK] GPIO released.")
    except Exception:
        pass

def is_off_hook(lgpio, h) -> bool:
    """Return True when the handset is lifted (pin reads HIGH)."""
    return lgpio.gpio_read(h, OFF_HOOK_PIN) == 1

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    lgpio, h = init_gpio()
    pub = Publisher(Topic.PHONE_HOOK)

    # Publish the initial state immediately at startup
    last_state = is_off_hook(lgpio, h)
    event = "lifted" if last_state else "hung_up"
    pub.send(PhoneHookMessage(state=event))
    print(f"Initial hook state: {event}")

    def handle_exit(sig, frame):
        pub.close()
        cleanup_gpio(lgpio, h)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Hook monitor running... (Ctrl+C to stop)\n")

    while True:
        state = is_off_hook(lgpio, h)
        if state != last_state:
            event = "lifted" if state else "hung_up"
            pub.send(PhoneHookMessage(state=event))
            print(f"Hook {event}")
            last_state = state
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
