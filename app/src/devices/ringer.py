"""
ringer.py — Telephone bell ringer driven by a PWM warble on a GPIO pin.

The ringer alternates between two frequencies (a "warble") to imitate a
telephone bell. start_ringing() rings in a repeating on/off cadence in the
background; stop_ringing() silences it immediately.
"""

import time
import threading

RINGER_PIN = 3

# Warble tone frequencies and how fast to alternate between them.
FREQ_A = 400
FREQ_B = 450
WARBLE_SWITCH_MS = 33

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
        import RPi.GPIO as GPIO
        self._GPIO = GPIO
        self._pin = pin
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self._pin, FREQ_A)
        print(f"[OK] Ringer ready on GPIO {self._pin}.")

    def _warble(self, duration: float) -> None:
        """Alternate between the two tones for *duration* s, or until stopped."""
        self._pwm.start(50)
        end_time = time.time() + duration
        use_a = True
        while time.time() < end_time and not self._stop_event.is_set():
            self._pwm.ChangeFrequency(FREQ_A if use_a else FREQ_B)
            use_a = not use_a
            self._stop_event.wait(WARBLE_SWITCH_MS / 1000.0)
        self._pwm.stop()

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
        self._pwm.stop()

    def close(self) -> None:
        """Stop ringing and release the GPIO pin."""
        self.stop_ringing()
        try:
            self._GPIO.cleanup(self._pin)
            print(f"[OK] Ringer GPIO {self._pin} released.")
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
