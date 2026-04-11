#!/bin/sh
set -eu

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn presentation.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips="*"