import sys
from messaging import Broker

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <topic> <message>")
    sys.exit(1)

topic = sys.argv[1]
message = sys.argv[2]

broker = Broker()
pub = broker.publisher()
pub.publish(topic, message)
pub.close()
