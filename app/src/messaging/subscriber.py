from __future__ import annotations
from typing import TYPE_CHECKING
import zmq

if TYPE_CHECKING:
    from messaging.broker import Broker


class Subscriber:
    """A SUB socket connected to the broker's dispatch endpoint."""

    def __init__(self, broker: Broker, topic: str = ""):
        """
        Connect to *broker* and subscribe to *topic*.
        Pass an empty string (default) to receive all messages.
        """
        self._socket = broker.subscribe_socket()
        self._socket.setsockopt(zmq.SUBSCRIBE, topic.encode())

    def receive(self) -> tuple[str, str]:
        """Block until a message arrives; return (topic, message)."""
        topic, message = self._socket.recv_multipart()
        return topic.decode(), message.decode()

    def close(self) -> None:
        self._socket.close()
