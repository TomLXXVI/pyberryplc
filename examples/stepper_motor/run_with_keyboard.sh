#!/bin/bash

# === CONFIGURATIE ===
PROJECT_DIR="/shared/python-projects/rpi-gpio/examples/stepper_motor"
VENV_PATH="/home/tom-chr/.virtualenvs/rpi-gpio"
SCRIPT="stepper_motor02.py"  # of jouw testscript

# === UITVOERING ===
cd "$PROJECT_DIR" || { echo "Directory not found"; exit 1; }

PYTHON="$VENV_PATH/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "Python not found in virtual environment: $PYTHON"
    exit 1
fi

echo "Execute script with virtual environment in sudo..."
sudo "$PYTHON" "$SCRIPT"
