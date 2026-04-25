#!/usr/bin/env sh
# Docker entrypoint for lms-api and lms-worker.
#
# Routing logic (based on $1 passed by CMD or dockerCommand):
#   api    → run alembic migrations, then start uvicorn (API service)
#   celery → skip migrations, exec the full celery command (worker service)
#   *      → pass-through for custom commands (e.g. shell debugging)
#
set -e

case "$1" in
  api)
    echo "[entrypoint] Running Alembic migrations..."
    alembic -c migrations/alembic.ini upgrade head
    echo "[entrypoint] Migrations complete. Starting API on port ${PORT:-8000}..."
    exec uvicorn app.main:create_app \
      --factory \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${WORKERS:-4}"
    ;;
  celery)
    echo "[entrypoint] Worker mode — skipping migrations."
    exec "$@"
    ;;
  *)
    echo "[entrypoint] Passthrough: $*"
    exec "$@"
    ;;
esac
