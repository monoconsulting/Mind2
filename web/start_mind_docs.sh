#!/bin/bash
# Mind2 Documentation Server (mind-docs) Startup Script
# This script starts the mind-docs web server automatically

# Change to script directory
cd "$(dirname "$0")"

echo "Starting Mind2 Documentation Server (mind-docs)..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH"
        echo "Please install Python 3.7 or higher and try again."
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Start the server
echo "Starting server on http://localhost:9091"
echo "Press Ctrl+C to stop the server"
echo ""
exec $PYTHON_CMD server.py