import threading
import zmq

PUBLISH_ENDPOINT = "tcp://127.0.0.1:5559"
SUBSCRIBE_ENDPOINT = "tcp://127.0.0.1:5560"


class Broker:
    """
    Message broker built on a ZMQ XSUB/XPUB proxy.

    Run this in its own process to relay messages between publishers and
    subscribers.  Clients need not import or know about the Broker at all —
    they simply create Publisher and Subscriber objects directly.

    Typical usage
    -------------
    # broker process:
        broker = Broker()
        broker.start()

    # publisher process:
        pub = Publisher("weather")
        pub.send("sunny")

    # subscriber process:
        sub = Subscriber("weather")
        topic, message = sub.receive()
    """

    def __init__(self):
        self._context = zmq.Context()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the XSUB/XPUB proxy in a daemon background thread."""
        if self._thread and self._thread.is_alive():
            return

        xsub = self._context.socket(zmq.XSUB)
        xsub.bind(PUBLISH_ENDPOINT)

        xpub = self._context.socket(zmq.XPUB)
        xpub.bind(SUBSCRIBE_ENDPOINT)

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
