#!/bin/sh
set -e

echo "[labpulse] running database migrations..."
alembic upgrade head

echo "[labpulse] starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
