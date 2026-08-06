from dataclasses import dataclass
from enum import StrEnum


class Topic(StrEnum):
    """Message topics used across the teletube application.

    Each topic has a corresponding dataclass that represents its payload.

        pub = Publisher(Topic.KEYPAD)
        pub.send(KeypadMessage(year_entered=1976))

        sub = Subscriber(Topic.KEYPAD, KeypadMessage)
        topic, msg = sub.receive()   # msg is a KeypadMessage
        print(msg.year_entered)      # 1976
    """

    KEYPAD = "keypad"
    PLAYER = "player"
    DISPLAY = "display"
    SYSTEM = "system"
    PHONE_HOOK = "phone_hook"


@dataclass
class KeypadMessage:
    year_entered: str


@dataclass
class PlayerMessage:
    command: str          # e.g. "play", "stop", "pause"
    video_id: str = ""


@dataclass
class DisplayMessage:
    command: str          # e.g. "show_year", "show_error", "clear"
    text: str = ""


@dataclass
class SystemMessage:
    status: str           # e.g. "ready", "busy", "error"
    detail: str = ""


@dataclass
class PhoneHookMessage:
    state: str            # "lifted" or "hung_up"
