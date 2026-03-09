#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python update_data.py || true
exec gunicorn -w 2 -b 127.0.0.1:5000 app:app
