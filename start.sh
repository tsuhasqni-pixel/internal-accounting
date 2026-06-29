#!/bin/bash
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"
if [ ! -f ".venv/bin/python" ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi
python app.py
