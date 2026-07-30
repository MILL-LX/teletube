import sys
import json
from messaging import Publisher

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <topic> <json-payload>")
    print(f"  e.g. {sys.argv[0]} keypad '{{\"year_entered\": 1976}}'")
    sys.exit(1)

topic = sys.argv[1]
payload = json.loads(sys.argv[2])

pub = Publisher(topic)
pub.send(payload)
pub.close()
