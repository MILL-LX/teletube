import signal
from messaging import Broker

broker = Broker()
broker.start()

# Keep the process alive until interrupted
signal.pause()
