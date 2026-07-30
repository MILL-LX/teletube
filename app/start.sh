#!/usr/bin/env bash
# Start the broker and monitor as background processes.
# Logs are written to broker.log and monitor.log in this directory.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="$SCRIPT_DIR/src/apps"

# Kill any previously running instances
pkill -f "apps/broker.py" 2>/dev/null
pkill -f "apps/monitor.py" 2>/dev/null

echo "Starting broker..."
cd "$APPS_DIR"
uv run python broker.py &
BROKER_PID=$!

# Give the broker a moment to bind its sockets
sleep 0.5

echo "Starting monitor..."
uv run python monitor.py &
MONITOR_PID=$!

echo "Broker  PID: $BROKER_PID"
echo "Monitor PID: $MONITOR_PID"

# Persist PIDs for stop.sh
echo "$BROKER_PID" > "$SCRIPT_DIR/broker.pid"
echo "$MONITOR_PID" > "$SCRIPT_DIR/monitor.pid"
