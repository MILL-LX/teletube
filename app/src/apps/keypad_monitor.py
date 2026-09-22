#!/usr/bin/env python3
"""
keypad_monitor.py — Reads the 4x3 keypad and publishes year entries.

Uses a state machine with two states:
  - ignoring_keypad: default; keypad is not scanned (hook is on-hook)
  - monitoring_keypad: keypad is actively scanned (hook is off-hook)

Transitions are driven by HookMessages received on the PHONE_HOOK topic.
While monitoring, digit keys accumulate in a buffer. # sends the buffer as a
KeypadMessage and * clears it. DTMF tones play while keys are held.
"""

import os
import sys
import time
import signal
import threading

from statemachine import StateMachine, State

from messaging import Publisher, Subscriber
from apps.message_topics import Topic, KeypadMessage, HookMessage, DisplayMessage
from devices.keypad import Keypad
from sound.dtmf import DtmfPlayer
import sound.speech as speech

from util import year_to_words
from devices.video_player import VideoPlayer

def _year_range_prompt(min_year: str, max_year: str) -> str:
    return (f"Please enter a year between {year_to_words(min_year)} "
            f"and {year_to_words(max_year)} followed by the pound sign.")

def precompute_messages(min_year: str, max_year: str) -> None:
    """Synthesize all static and year-specific messages at startup."""
    prompt = _year_range_prompt(min_year, max_year)
    messages = {
        "keypad_monitor.prompt":          prompt,
        "keypad_monitor.prompt_cleared":  "Input cleared. " + prompt,
        "keypad_monitor.too_many_digits": "Too many digits entered. " + prompt,
    }
    for year in range(int(min_year), int(max_year) + 1):
        spoken = year_to_words(str(year))
        messages[f"keypad_monitor.chose_{year}"] = f"You chose {spoken}."
        messages[f"keypad_monitor.no_videos_{year}"] = (
            f"Sorry! No videos available for {spoken}."
        )
    speech.precompute(messages)

# ── State machine ─────────────────────────────────────────────────────────
class KeypadStateMachine(StateMachine):
    """Manages whether the keypad is actively monitored."""

    ignoring_keypad  = State(initial=True)
    monitoring_keypad = State()

    hook_lifted = ignoring_keypad.to(monitoring_keypad)
    hook_hung_up = monitoring_keypad.to(ignoring_keypad)

    def __init__(self, pub: Publisher, display_pub: Publisher,
                 dtmf_player: DtmfPlayer, video_player: VideoPlayer,
                 min_year: str, max_year: str):
        self._pub = pub
        self._display_pub = display_pub
        self._dtmf_player = dtmf_player
        self._video_player = video_player
        self._min_year = min_year
        self._max_year = max_year
        # Three-line on-screen prompt: what to do, the valid range, and how to confirm.
        self._display_prompt = f"ENTER A YEAR\n{min_year}-{max_year}\nTHEN PRESS #"
        self._buffer = ""
        self._current_key: str | None = None
        self._key_pressed = threading.Event()
        super().__init__()

    def on_enter_ignoring_keypad(self):
        """Clear state when the hook is hung up."""
        self._key_pressed.set()  # stops the prompt loop if running
        speech.stop()
        self._dtmf_player.stop()
        # Note: don't touch the screen here. On hang-up, display_monitor's hook
        # handler takes over the screen (blinking "Pick Me Up!"). Publishing a
        # clear here would race with and cancel that blink.
        self._buffer = ""
        self._current_key = None
        print("Ignoring keypad.")

    def on_enter_monitoring_keypad(self):
        print("Monitoring keypad.")
        self._key_pressed.clear()
        self._display_pub.send(DisplayMessage(text=self._display_prompt))
        def _prompt_loop():
            time.sleep(1.5)
            while (self.monitoring_keypad in self.configuration
                   and not self._key_pressed.is_set()):
                speech.play_precomputed("keypad_monitor.prompt")
                self._key_pressed.wait(timeout=7)
        threading.Thread(target=_prompt_loop, daemon=True).start()

    def _reject_year(self, input_cleared: bool = False) -> None:
        """Clear the buffer and prompt the user to try again."""
        print(f"Rejected year: {self._buffer!r}")
        self._buffer = ""
        self._display_pub.send(DisplayMessage(text=self._display_prompt))
        key = "keypad_monitor.prompt_cleared" if input_cleared else "keypad_monitor.prompt"
        threading.Thread(
            target=speech.play_precomputed,
            args=(key,),
            daemon=True,
        ).start()

    def _no_videos(self, year: str) -> None:
        """Show a 'no videos' message for *year*, linger, then resume data entry."""
        print(f"No videos available for {year}.")
        self._buffer = ""
        self._display_pub.send(
            DisplayMessage(text=f"Sorry!\nNo Videos Available\nfor {year}", size=62)
        )
        threading.Thread(
            target=speech.play_precomputed,
            args=(f"keypad_monitor.no_videos_{year}",),
            daemon=True,
        ).start()

        def _linger():
            time.sleep(5)
            # Only resume if we're still monitoring and the user hasn't started
            # typing again in the meantime.
            if self.monitoring_keypad in self.configuration and not self._buffer:
                self._display_pub.send(DisplayMessage(text=self._display_prompt))
                speech.play_precomputed("keypad_monitor.prompt")
        threading.Thread(target=_linger, daemon=True).start()

    def process_key(self, keypad: Keypad) -> None:
        """Scan the keypad and act on press/release. Call only while monitoring."""
        key = keypad.scan()

        if key != self._current_key:
            if self._current_key is not None:
                self._dtmf_player.stop()

            if key is not None:
                self._key_pressed.set()
                speech.stop()
                self._dtmf_player.play(key)

                if key == "#":
                    if not (self._buffer and self._min_year <= self._buffer <= self._max_year):
                        self._reject_year()
                    elif not self._video_player.has_videos_for_year(self._buffer):
                        self._no_videos(self._buffer)
                    else:
                        year = self._buffer
                        self._pub.send(KeypadMessage(year_entered=year))
                        print(f"Sent: year_entered={year!r}")
                        threading.Thread(
                            target=speech.play_precomputed,
                            args=(f"keypad_monitor.chose_{year}",),
                            daemon=True,
                        ).start()
                        self._buffer = ""
                elif key == "*":
                    print(f"Buffer cleared (was: {self._buffer!r})")
                    self._reject_year(input_cleared=True)
                else:
                    self._buffer += key
                    print(f"Buffer: {self._buffer}")
                    if len(self._buffer) > 4:
                        print("Too many digits entered.")
                        self._buffer = ""
                        self._display_pub.send(DisplayMessage(text=self._display_prompt))
                        threading.Thread(
                            target=speech.play_precomputed,
                            args=("keypad_monitor.too_many_digits",),
                            daemon=True,
                        ).start()
                    else:
                        # Show the digits entered so far in place of the prompt.
                        self._display_pub.send(DisplayMessage(text=self._buffer))

            self._current_key = key

# ── Hook listener ─────────────────────────────────────────────────────────
def hook_listener(sm: KeypadStateMachine) -> None:
    """Background thread: receives HookMessages and drives transitions."""
    sub = Subscriber(Topic.PHONE_HOOK, HookMessage)
    while True:
        _, msg = sub.receive()
        if msg.state == "lifted" and sm.monitoring_keypad not in sm.configuration:
            sm.hook_lifted()
        elif msg.state == "hung_up" and sm.monitoring_keypad in sm.configuration:
            sm.hook_hung_up()

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    keypad       = Keypad()
    video_player = VideoPlayer()
    min_year, max_year = video_player.year_range()
    precompute_messages(min_year, max_year)
    pub         = Publisher(Topic.KEYPAD)
    display_pub = Publisher(Topic.DISPLAY)
    dtmf_player = DtmfPlayer()
    sm          = KeypadStateMachine(pub, display_pub, dtmf_player, video_player, min_year, max_year)

    thread = threading.Thread(target=hook_listener, args=(sm,), daemon=True)
    thread.start()

    def handle_exit(sig, frame):
        # Best-effort cleanup, but never let a blocking teardown (e.g. audio
        # stream shutdown) hold up the process — force-exit when done.
        try:
            dtmf_player.stop()
            pub.close()
            display_pub.close()
            keypad.close()
        finally:
            os._exit(0)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Keypad monitor running... (Ctrl+C to stop)")
    print("Waiting for hook to be lifted.\n")

    while True:
        if sm.monitoring_keypad in sm.configuration:
            sm.process_key(keypad)
        time.sleep(0.02)

if __name__ == "__main__":
    main()
