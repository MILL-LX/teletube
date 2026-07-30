import zmq

from messaging.broker import SUBSCRIBE_ENDPOINT


class Subscriber:
    """A SUB socket that receives messages from the broker on a fixed topic."""

    def __init__(self, topic: str = ""):
        """
        Subscribe to *topic*.
        Pass an empty string (default) to receive all messages.
        """
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect(SUBSCRIBE_ENDPOINT)
        self._socket.setsockopt(zmq.SUBSCRIBE, topic.encode())

    def receive(self) -> tuple[str, str]:
        """Block until a message arrives; return (topic, message)."""
        topic, message = self._socket.recv_multipart()
        return topic.decode(), message.decode()

    def close(self) -> None:
        self._socket.close()
        self._context.term()
