#!/bin/bash
# ── LMS Celery Worker — Codespace Remote Muscle ───────────────────────────────
# Connects to the live Render PostgreSQL + Redis and processes background tasks.
#
# Usage (from project root or backend/):
#   bash backend/scripts/start_worker.sh
#
# Required env vars (set these before running, or export them in your shell):
#   DATABASE_URL - Render external PostgreSQL URL
#   REDIS_URL    - Render external Redis URL  (note: uses rediss:// for TLS)
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$(cd "$BACKEND_DIR/.." && pwd)/venv"

cd "$BACKEND_DIR"

# Activate virtualenv if present
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    source "$VENV_DIR/bin/activate"
    echo "[worker] Using venv: $VENV_DIR"
fi

# Guard: require DATABASE_URL and REDIS_URL
if [[ -z "${DATABASE_URL}" ]]; then
    echo "[worker] ERROR: DATABASE_URL is not set."
    echo "  export DATABASE_URL='postgresql://school_user:...@.../school_management_hhcg'"
    exit 1
fi

if [[ -z "${REDIS_URL}" ]]; then
    echo "[worker] ERROR: REDIS_URL is not set."
    echo "  export REDIS_URL='rediss://red-...@oregon-keyvalue.render.com:6379'"
    exit 1
fi

if [[ -z "${OPENAI_API_KEY}" ]]; then
    echo "[worker] WARNING: OPENAI_API_KEY is not set — AI grading tasks will return empty feedback."
fi

# The Celery app uses CELERY_BROKER_URL / CELERY_RESULT_BACKEND env vars.
# On Render the broker and backend both point at the same Redis instance.
# Celery reads these env vars before our _tls_url() helper runs, so we must
# embed ssl_cert_reqs=none directly in the URL passed via env.
_REDIS_TLS="${REDIS_URL}?ssl_cert_reqs=none"
export CELERY_BROKER_URL="${_REDIS_TLS}"
export CELERY_RESULT_BACKEND="${_REDIS_TLS}"

echo "[worker] Starting Celery worker..."
echo "[worker] Queue: grading, email, notifications, celery"

exec celery -A app.tasks.celery_app worker \
    --loglevel=info \
    -Q grading,email,notifications,celery \
    --concurrency=4 \
    --max-tasks-per-child=100
