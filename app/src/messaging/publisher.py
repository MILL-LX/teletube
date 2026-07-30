import dataclasses
import json
import time
import zmq

from messaging.broker import PUBLISH_ENDPOINT

_CONNECT_DELAY = 0.5  # seconds to wait after connecting before sending


class Publisher:
    """A PUB socket that sends dataclass messages to the broker on a fixed topic."""

    def __init__(self, topic: str):
        self._topic = topic
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.connect(PUBLISH_ENDPOINT)
        time.sleep(_CONNECT_DELAY)

    def send(self, payload: object) -> None:
        """Serialize *payload* (a dataclass instance) to JSON and send it."""
        self._socket.send_multipart([
            self._topic.encode(),
            json.dumps(dataclasses.asdict(payload)).encode(),
        ])

    def close(self) -> None:
        self._socket.close()
        self._context.term()
