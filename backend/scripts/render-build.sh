#!/usr/bin/env bash
# Render.com build script for the LMS FastAPI backend.
# Runs during the "Build Command" phase, before the web service starts.
# Exit immediately on any error.
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Exporting OpenAPI schema for frontend team..."
python scripts/export_openapi.py

echo "==> Build complete."
