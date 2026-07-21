#!/usr/bin/env bash
set -euo pipefail

# Set to true to cd into ABSOLUTE_PATH instead of auto-detecting the script's
# own directory. Useful when launched from autostart/.desktop entries, where
# relative path resolution can be unreliable.
USE_ABSOLUTE_PATH=false
ABSOLUTE_PATH="/home/vincent/Documents/Project Interaction/Local-Printer-Code"

if [ "$USE_ABSOLUTE_PATH" = true ]; then
    cd "$ABSOLUTE_PATH"
else
    cd "$(dirname "$0")"
fi

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

source venv/bin/activate
exec python3 installation.py
