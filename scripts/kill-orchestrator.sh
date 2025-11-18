#!/bin/bash

# Kill Orchestrator Script
# This script finds and kills any running orchestrator processes

echo "🔍 Looking for orchestrator processes..."

# Find orchestrator processes (multiple patterns)
ORCHESTRATOR_PIDS=$(ps aux | grep -E "(uvicorn.*app\.main|orchestrator.*uvicorn|python.*uvicorn.*app\.main)" | grep -v grep | awk '{print $2}')

# Also check for any python processes running main.py from orchestrator
PYTHON_PIDS=$(ps aux | grep "python.*orchestrator.*main\.py" | grep -v grep | awk '{print $2}')

# Combine all found PIDs
ALL_PIDS="$ORCHESTRATOR_PIDS $PYTHON_PIDS"

if [ -z "$ALL_PIDS" ]; then
    echo "✅ No orchestrator processes found running."
    exit 0
fi

echo "📋 Found orchestrator processes:"
for PID in $ALL_PIDS; do
    if [ ! -z "$PID" ] && [ "$PID" != " " ]; then
        PROCESS_INFO=$(ps -p $PID -o pid,ppid,cmd 2>/dev/null | tail -n 1)
        if [ ! -z "$PROCESS_INFO" ]; then
            echo "   PID $PID: $PROCESS_INFO"
        fi
    fi
done

echo ""
echo "🛑 Killing orchestrator processes..."

# Try graceful shutdown first
for PID in $ALL_PIDS; do
    echo "   📤 Sending SIGTERM to PID $PID..."
    kill -TERM $PID 2>/dev/null

    # Wait a moment for graceful shutdown
    sleep 2

    # Check if process is still running
    if kill -0 $PID 2>/dev/null; then
        echo "   ⚠️ Process $PID still running, sending SIGKILL..."
        kill -KILL $PID 2>/dev/null
    else
        echo "   ✅ Process $PID terminated gracefully"
    fi
done

# Final check
sleep 1
REMAINING_UVICORN=$(ps aux | grep -E "(uvicorn.*app\.main|orchestrator.*uvicorn)" | grep -v grep | wc -l)
REMAINING_PYTHON=$(ps aux | grep "python.*orchestrator.*main\.py" | grep -v grep | wc -l)
REMAINING=$((REMAINING_UVICORN + REMAINING_PYTHON))
if [ $REMAINING -eq 0 ]; then
    echo "🎉 All orchestrator processes successfully terminated!"
else
    echo "⚠️ $REMAINING orchestrator processes still running. You may need to kill them manually."
fi

echo ""
echo "💡 Tip: You can also use these HTTP endpoints to shutdown gracefully:"
echo "   curl -X POST http://localhost:9000/shutdown"
echo "   curl -X POST http://localhost:9000/force-shutdown"
echo "   curl -X POST http://localhost:9000/kill-orchestrator"
