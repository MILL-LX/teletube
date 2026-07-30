import json
import zmq

from messaging.broker import SUBSCRIBE_ENDPOINT


class Subscriber:
    """A SUB socket that receives and deserializes messages from the broker."""

    def __init__(self, topic: str = "", message_type: type = None):
        """
        Subscribe to *topic* and decode received messages into *message_type*.
        Pass an empty string for *topic* to receive all messages.
        If *message_type* is omitted, receive() returns a plain dict.
        """
        self._message_type = message_type
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect(SUBSCRIBE_ENDPOINT)
        self._socket.setsockopt(zmq.SUBSCRIBE, topic.encode())

    def receive(self) -> tuple[str, object]:
        """Block until a message arrives.

        Returns (topic, payload) where payload is an instance of the
        message_type passed at construction, or a plain dict if none was given.
        """
        topic, message = self._socket.recv_multipart()
        data = json.loads(message.decode())
        payload = self._message_type(**data) if self._message_type else data
        return topic.decode(), payload

    def close(self) -> None:
        self._socket.close()
        self._context.term()
