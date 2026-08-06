#!/usr/bin/env bash
# Start the broker and monitor as background processes.
# Logs are written to broker.log and monitor.log in this directory.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
PID_DIR="/tmp/teletube"
export PYTHONPATH="$SRC_DIR"

mkdir -p "$PID_DIR"

# Stop any previously running instances and wait for ports to be released
"$SCRIPT_DIR/stop.sh"
sleep 1

echo "Starting broker..."
cd "$SRC_DIR"
uv run python apps/broker.py &
BROKER_PID=$!

# Give the broker a moment to bind its sockets
sleep 2

echo "Starting monitor..."
uv run python apps/monitor.py &
MONITOR_PID=$!

echo "Starting keypad monitor..."
uv run python apps/keypad_monitor.py &
KEYPAD_PID=$!

echo "Starting hook monitor..."
uv run python apps/hook_monitor.py &
HOOK_PID=$!

echo "Broker         PID: $BROKER_PID"
echo "Monitor        PID: $MONITOR_PID"
echo "Keypad monitor PID: $KEYPAD_PID"
echo "Hook monitor   PID: $HOOK_PID"

# Persist PIDs for stop.sh
echo "$BROKER_PID" > "$PID_DIR/broker.pid"
echo "$MONITOR_PID" > "$PID_DIR/monitor.pid"
echo "$KEYPAD_PID"  > "$PID_DIR/keypad_monitor.pid"
echo "$HOOK_PID"    > "$PID_DIR/hook_monitor.pid"
