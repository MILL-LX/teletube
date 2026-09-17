"""
hook.py — GPIO initialisation and reading for the telephone hook switch.
"""

import sys

OFF_HOOK_PIN = 12


class Hook:
    """Owns the GPIO handle for the telephone hook switch.

    Initialises GPIO on construction and releases it on close().
    Use as a context manager for automatic cleanup:

        with Hook() as hook:
            if hook.is_off_hook():
                ...
    """

    def __init__(self):
        try:
            import lgpio
            self._lgpio = lgpio
            self._h = lgpio.gpiochip_open(0)
            if self._h < 0:
                print("[ERROR] Could not open GPIO chip.")
                sys.exit(1)
            lgpio.gpio_claim_input(self._h, OFF_HOOK_PIN, lgpio.SET_PULL_UP)
            print(f"[OK] GPIO {OFF_HOOK_PIN} ready with pull-up.")
        except ImportError:
            print("[ERROR] lgpio not installed.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    def is_off_hook(self) -> bool:
        """Return True when the handset is lifted (pin reads HIGH)."""
        return self._lgpio.gpio_read(self._h, OFF_HOOK_PIN) == 1

    def close(self) -> None:
        """Release the GPIO handle."""
        try:
            self._lgpio.gpiochip_close(self._h)
            print("[OK] GPIO released.")
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
