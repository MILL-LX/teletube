from dataclasses import dataclass
from enum import StrEnum


class Topic(StrEnum):
    """Message topics used across the teletube application.

    Each topic has a corresponding dataclass that represents its payload.

        pub = Publisher(Topic.KEYPAD)
        pub.send(KeypadMessage(year_entered="1976"))

        sub = Subscriber(Topic.KEYPAD, KeypadMessage)
        topic, msg = sub.receive()   # msg is a KeypadMessage
        print(msg.year_entered)      # "1976"
    """

    KEYPAD     = "keypad"
    PHONE_HOOK = "phone_hook"
    DISPLAY    = "display"
    PLAYBACK   = "playback"


@dataclass
class KeypadMessage:
    year_entered: str


@dataclass
class HookMessage:
    state: str            # "lifted" or "hung_up"


@dataclass
class DisplayMessage:
    # Text to show on screen. A blank string clears the screen.
    # Use newlines to split the text across multiple lines.
    text: str = ""
    # Font size in points. None means use the display monitor's default size.
    size: int | None = None


@dataclass
class PlaybackMessage:
    command: str            # "hint": briefly interrupt the video to show a hint
    text: str = ""          # for "hint": the chosen year, named in the hint
    duration: float = 3.0   # for "hint": seconds to show the hint
