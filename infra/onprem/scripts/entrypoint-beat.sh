#!/usr/bin/env bash
set -euo pipefail
echo "[kestrel] starting Celery beat in deployment mode: ${KESTREL_DEPLOYMENT_MODE:-cloud}"
exec celery -A app.tasks.celery_app.celery_app beat --loglevel=INFO
