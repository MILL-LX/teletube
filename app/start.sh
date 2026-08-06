#!/usr/bin/env bash
# Start the broker and monitor as background processes.
# Logs are written to broker.log and monitor.log in this directory.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
export PYTHONPATH="$SRC_DIR"

# Kill any previously running instances and wait for ports to be released
pkill -f "broker.py" 2>/dev/null
pkill -f "monitor.py" 2>/dev/null
pkill -f "keypad_monitor.py" 2>/dev/null
pkill -f "hook_monitor.py" 2>/dev/null
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
echo "$BROKER_PID" > "$SCRIPT_DIR/broker.pid"
echo "$MONITOR_PID" > "$SCRIPT_DIR/monitor.pid"
echo "$KEYPAD_PID"  > "$SCRIPT_DIR/keypad_monitor.pid"
echo "$HOOK_PID"    > "$SCRIPT_DIR/hook_monitor.pid"
