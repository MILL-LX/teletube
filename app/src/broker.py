import zmq

from messaging.config import PUBLISH_ENDPOINT, SUBSCRIBE_ENDPOINT

"""
Message broker for nodes to communicate
"""

context = zmq.Context()

# Nodes connect here to PUBLISH
publish = context.socket(zmq.XSUB)
publish.bind(PUBLISH_ENDPOINT)

# Nodes connect here to SUBSCRIBE
subscribe = context.socket(zmq.XPUB)
subscribe.bind(SUBSCRIBE_ENDPOINT)

print("Broker running...")
zmq.proxy(publish, subscribe)