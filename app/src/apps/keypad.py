"""
keypad_gpio.py — GPIO initialisation and scanning for the 4x3 keypad.
"""

import sys
import time

ROW_PINS    = [16, 6, 13, 19]
COLUMN_PINS = [26, 20, 21]

KEY_MAP = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["*", "0", "#"],
]


class Keypad:
    """Owns the GPIO handle for the 4x3 keypad.

    Initialises GPIO on construction and releases it on close().
    Use as a context manager for automatic cleanup:

        with Keypad() as keypad:
            key = keypad.scan()
    """

    def __init__(self):
        try:
            import lgpio
            self._lgpio = lgpio
            self._h = lgpio.gpiochip_open(0)
            if self._h < 0:
                print("[ERROR] Could not open GPIO chip.")
                sys.exit(1)
            for row in ROW_PINS:
                lgpio.gpio_claim_output(self._h, row, 0)
            for col in COLUMN_PINS:
                lgpio.gpio_claim_input(self._h, col, lgpio.SET_PULL_DOWN)
            print(f"[OK] GPIO ready. Rows: {ROW_PINS}  Cols: {COLUMN_PINS}")
        except ImportError:
            print("[ERROR] lgpio not installed.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    def scan(self) -> str | None:
        """Return the key that is currently pressed, or None."""
        for i, row in enumerate(ROW_PINS):
            for r in ROW_PINS:
                self._lgpio.gpio_write(self._h, r, 1 if r == row else 0)
            time.sleep(0.005)
            for j, col in enumerate(COLUMN_PINS):
                if self._lgpio.gpio_read(self._h, col):
                    return KEY_MAP[i][j]
        return None

    def close(self) -> None:
        """Release all GPIO pins and close the chip handle."""
        try:
            for row in ROW_PINS:
                self._lgpio.gpio_write(self._h, row, 0)
            self._lgpio.gpiochip_close(self._h)
            print("[OK] GPIO released.")
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
