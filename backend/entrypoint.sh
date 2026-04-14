#!/bin/sh
set -e

echo "Starting Dyz-Art MAS Backend..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
