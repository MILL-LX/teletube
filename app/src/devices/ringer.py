"""
ringer.py — Telephone bell ringer driven by a PWM warble on a GPIO pin.

The ringer alternates between two frequencies (a "warble") to imitate a
telephone bell. start_ringing() rings in a repeating on/off cadence in the
background; stop_ringing() silences it immediately.

Uses lgpio (the same GPIO library as the other devices) with software-timed
PWM (lgpio.tx_pwm).
"""

import sys
import time
import threading

RINGER_PIN = 3

# Warble tone frequencies and how fast to alternate between them.
FREQ_A = 400
FREQ_B = 450
WARBLE_SWITCH_MS = 33
DUTY_CYCLE = 50   # percent

# Ring cadence: how long the bell sounds, then how long it rests, per cycle.
RING_ON_TIME = 1.5
RING_OFF_TIME = 1.0


class Ringer:
    """Drives the telephone bell via a PWM warble on RINGER_PIN.

    Use as a context manager for automatic cleanup:

        with Ringer() as ringer:
            ringer.start_ringing()
            ...
            ringer.stop_ringing()
    """

    def __init__(self, pin: int = RINGER_PIN):
        try:
            import lgpio
            self._lgpio = lgpio
            self._pin = pin
            self._h = lgpio.gpiochip_open(0)
            if self._h < 0:
                print("[ERROR] Could not open GPIO chip.")
                sys.exit(1)
            lgpio.gpio_claim_output(self._h, pin, 0)
            print(f"[OK] Ringer ready on GPIO {pin}.")
        except ImportError:
            print("[ERROR] lgpio not installed.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _set_tone(self, freq: int) -> None:
        """Emit a PWM tone at *freq* Hz, or silence the pin when freq is 0.

        To silence, set a 0% duty cycle at a valid frequency: this actually
        stops the PWM generator's output (a plain gpio_write is overridden by
        the still-running PWM, and tx_pwm with a 0 frequency raises
        'bad PWM micros').
        """
        if freq:
            self._lgpio.tx_pwm(self._h, self._pin, freq, DUTY_CYCLE)
        else:
            self._lgpio.tx_pwm(self._h, self._pin, FREQ_A, 0)

    def _warble(self, duration: float) -> None:
        """Alternate between the two tones for *duration* s, or until stopped."""
        end_time = time.time() + duration
        use_a = True
        while time.time() < end_time and not self._stop_event.is_set():
            self._set_tone(FREQ_A if use_a else FREQ_B)
            use_a = not use_a
            self._stop_event.wait(WARBLE_SWITCH_MS / 1000.0)
        self._set_tone(0)

    def _run(self) -> None:
        """Repeat the ring on/off cadence until stopped."""
        while not self._stop_event.is_set():
            self._warble(RING_ON_TIME)
            if self._stop_event.is_set():
                break
            self._stop_event.wait(RING_OFF_TIME)

    def start_ringing(self) -> None:
        """Start ringing in the background (no-op if already ringing)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop_ringing(self) -> None:
        """Stop ringing immediately."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None
        self._set_tone(0)

    def close(self) -> None:
        """Stop ringing and release the GPIO pin."""
        self.stop_ringing()
        try:
            self._lgpio.gpiochip_close(self._h)
            print(f"[OK] Ringer GPIO {self._pin} released.")
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
