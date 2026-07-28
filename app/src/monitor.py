from messaging import Broker

broker = Broker()
sub = broker.subscriber()  # no topic = receive everything

print("Monitoring... Ctrl+C to stop")
while True:
    topic, message = sub.receive()
    print(f"[{topic}] {message}")
