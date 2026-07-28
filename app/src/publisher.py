import sys
import zmq
import time

from messaging.config import PUBLISH_ENDPOINT

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <topic> <message>")
    sys.exit(1)

topic = sys.argv[1]
message = sys.argv[2]

context = zmq.Context()
pub = context.socket(zmq.PUB)
pub.connect(PUBLISH_ENDPOINT)

# Allow time for the connection + subscription handshake to complete
time.sleep(0.5)

pub.send_string(f"{topic} {message}")
