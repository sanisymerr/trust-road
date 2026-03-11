#!/bin/bash
set -e

cd "$(dirname "$0")"
source .venv/bin/activate
python update_data.py >> data/update.log 2>&1
