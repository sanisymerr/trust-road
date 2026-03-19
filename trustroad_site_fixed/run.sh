#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ "${RUN_INITIAL_UPDATE:-0}" = "1" ]; then
  python update_data.py
fi

exec gunicorn -w 1 --timeout 300 -b 0.0.0.0:${PORT:-10000} app:app
