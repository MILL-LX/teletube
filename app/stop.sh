#!/usr/bin/env bash
# Stop the broker and monitor started by start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

stop_proc() {
    local name=$1
    local pidfile="$SCRIPT_DIR/${name}.pid"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $name (PID $pid)..."
            kill "$pid"
        else
            echo "$name is not running."
        fi
        rm -f "$pidfile"
    else
        echo "No PID file for $name; trying pkill..."
        pkill -f "${name}.py" 2>/dev/null
    fi
}

stop_proc broker
stop_proc monitor
