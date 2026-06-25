#!/bin/bash
# run_daily_current_affairs.sh
# Shell script to run the daily current affairs generation command on Hostinger VPS

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== Current Affairs Generation Started: $(date) ==="

# Activate Python virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: virtualenv not found at $SCRIPT_DIR/venv"
    exit 1
fi

# Run Django management command
python manage.py generate_current_affairs

echo "=== Current Affairs Generation Finished: $(date) ==="
echo ""
