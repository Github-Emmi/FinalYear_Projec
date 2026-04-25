#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source ../venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info -Q grading,email,notifications,celery
