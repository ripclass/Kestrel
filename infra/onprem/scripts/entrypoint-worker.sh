#!/usr/bin/env bash
set -euo pipefail
echo "[kestrel] starting Celery worker in deployment mode: ${KESTREL_DEPLOYMENT_MODE:-cloud}"
exec celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO
