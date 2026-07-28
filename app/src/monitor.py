import zmq

from messaging.config import SUBSCRIBE_ENDPOINT

context = zmq.Context()
sub = context.socket(zmq.SUB)
sub.connect(SUBSCRIBE_ENDPOINT)
sub.setsockopt_string(zmq.SUBSCRIBE, "")  # everything

print("Monitoring... Ctrl+C to stop")
while True:
    print(sub.recv_string())