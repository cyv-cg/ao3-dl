#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
    echo "Installing dependencies..."
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
fi

. $VENV_DIR/bin/activate
python3 $SCRIPT_DIR/ao3-dl.py "$@"
deactivate

