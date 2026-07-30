import time
import zmq

from messaging.broker import PUBLISH_ENDPOINT

_CONNECT_DELAY = 0.5  # seconds to wait after connecting before sending


class Publisher:
    """A PUB socket that sends messages to the broker on a fixed topic."""

    def __init__(self, topic: str):
        self._topic = topic
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.connect(PUBLISH_ENDPOINT)
        time.sleep(_CONNECT_DELAY)

    def send(self, message: str) -> None:
        """Send *message* on the topic this publisher was created with."""
        self._socket.send_multipart([self._topic.encode(), message.encode()])

    def close(self) -> None:
        self._socket.close()
        self._context.term()
