import time
import threading
import zmq

from messaging.publisher import Publisher
from messaging.subscriber import Subscriber

_PUBLISH_ENDPOINT = "tcp://127.0.0.1:5559"
_SUBSCRIBE_ENDPOINT = "tcp://127.0.0.1:5560"
_CONNECT_DELAY = 0.5  # seconds to wait after connecting before sending


class Broker:
    """
    Message broker built on a ZMQ XSUB/XPUB proxy.

    Typical usage
    -------------
    # In the broker process:
        broker = Broker()
        broker.start()          # runs the proxy in a background thread

    # In any client process:
        broker = Broker()
        pub = broker.publisher()
        pub.publish("topic", "hello")

        sub = broker.subscriber("topic")
        topic, message = sub.receive()
    """

    def __init__(self):
        self._context = zmq.Context()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Broker lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the XSUB/XPUB proxy in a daemon background thread."""
        if self._thread and self._thread.is_alive():
            return

        xsub = self._context.socket(zmq.XSUB)
        xsub.bind(_PUBLISH_ENDPOINT)

        xpub = self._context.socket(zmq.XPUB)
        xpub.bind(_SUBSCRIBE_ENDPOINT)

        self._thread = threading.Thread(
            target=zmq.proxy,
            args=(xsub, xpub),
            daemon=True,
        )
        self._thread.start()
        print("Broker running...")

    def stop(self) -> None:
        """Terminate the ZMQ context, which unblocks the proxy thread."""
        self._context.term()
        if self._thread:
            self._thread.join(timeout=2)
        print("Broker stopped.")

    # ------------------------------------------------------------------
    # Socket factories (used by Publisher and Subscriber)
    # ------------------------------------------------------------------

    def publish_socket(self) -> zmq.Socket:
        """Return a connected PUB socket with the handshake delay applied."""
        sock = self._context.socket(zmq.PUB)
        sock.connect(_PUBLISH_ENDPOINT)
        time.sleep(_CONNECT_DELAY)
        return sock

    def subscribe_socket(self) -> zmq.Socket:
        """Return a connected SUB socket."""
        sock = self._context.socket(zmq.SUB)
        sock.connect(_SUBSCRIBE_ENDPOINT)
        return sock

    # ------------------------------------------------------------------
    # Client factories
    # ------------------------------------------------------------------

    def publisher(self) -> Publisher:
        """Return a Publisher connected to this broker."""
        return Publisher(self)

    def subscriber(self, topic: str = "") -> Subscriber:
        """Return a Subscriber connected to this broker.

        Pass a *topic* to filter messages; omit it (or pass an empty string)
        to receive everything.
        """
        return Subscriber(self, topic)
