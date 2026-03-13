#!/bin/bash
set -e
cd "$(dirname "$0")"

source .venv/bin/activate || true
python update_data.py || true

exec gunicorn -w 1 --timeout 300 -b 0.0.0.0:${PORT:-10000} app:app