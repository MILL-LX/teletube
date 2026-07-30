import sys
from messaging import Publisher

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <topic> <message>")
    sys.exit(1)

topic = sys.argv[1]
message = sys.argv[2]

pub = Publisher(topic)
pub.send(message)
pub.close()
