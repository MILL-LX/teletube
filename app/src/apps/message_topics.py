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


@dataclass
class KeypadMessage:
    year_entered: str


@dataclass
class PhoneHookMessage:
    state: str            # "lifted" or "hung_up"
