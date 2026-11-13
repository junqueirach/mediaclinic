#!/usr/bin/env sh
# MediaClinic for Linux and macOS: runs the app from source (v0.19.6, TR8).
# Needs Python 3.10 or newer with Tk, plus Pillow and openpyxl.
#   Debian / Ubuntu:  sudo apt install python3-tk python3-venv ffmpeg xdg-utils fonts-noto-color-emoji
#   (xdg-utils opens files and folders; the emoji font draws the icons. Desktop Ubuntu has both, WSL has neither.)
#   then, once:       python3 -m venv .venv && .venv/bin/pip install pillow openpyxl
# Settings go to ~/.config/MediaMetadataClinic/ ; logs to logs/app.log next to this file.
cd "$(dirname "$0")" || exit 1

PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python

if ! "$PY" -c "import tkinter" 2>/dev/null; then
    echo "Tk for Python is missing. Debian / Ubuntu: sudo apt install python3-tk (Fedora: python3-tkinter)."
    exit 1
fi
if ! "$PY" -c "import PIL, openpyxl" 2>/dev/null; then
    echo "Pillow or openpyxl is missing. Once:  python3 -m venv .venv && .venv/bin/pip install pillow openpyxl"
    exit 1
fi

if [ -f mediaclinic.py ]; then
    MAIN=mediaclinic.py
else
    MAIN=$(ls mediaclinic_v*.py 2>/dev/null | sort -V | tail -n 1)
fi
if [ -z "$MAIN" ]; then
    echo "mediaclinic.py was not found next to this script."
    exit 1
fi
exec "$PY" "$MAIN" "$@"
