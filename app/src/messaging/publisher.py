from __future__ import annotations
from typing import TYPE_CHECKING
import zmq

if TYPE_CHECKING:
    from messaging.broker import Broker


class Publisher:
    """A PUB socket connected to the broker's ingest endpoint."""

    def __init__(self, broker: Broker):
        self._socket = broker.publish_socket()

    def publish(self, topic: str, message: str) -> None:
        self._socket.send_multipart([topic.encode(), message.encode()])

    def close(self) -> None:
        self._socket.close()
