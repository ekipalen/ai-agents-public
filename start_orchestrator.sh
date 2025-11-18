#!/bin/bash

# Get the directory where the script is located to ensure relative paths work correctly
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Navigating to orchestrator directory..."
cd "$SCRIPT_DIR/orchestrator"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run the setup in the README."
    exit 1
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Starting Orchestrator on http://0.0.0.0:9000"
uvicorn app.main:app --host 0.0.0.0 --port 9000 --loop asyncio
