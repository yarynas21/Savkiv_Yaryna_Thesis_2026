#!/bin/sh
set -e

echo "Starting Dyz-Art MAS Backend..."
python -m db.migrate
exec uvicorn main:app --host 0.0.0.0 --port 8000
