#!/usr/bin/env bash
# FastAPI entrypoint. Runs migrations + license sync, then uvicorn.
set -euo pipefail

echo "[kestrel] starting engine in deployment mode: ${KESTREL_DEPLOYMENT_MODE:-cloud}"

# Apply pending migrations idempotently. Bootstrap exits non-zero on failure
# so the container restart loop holds until the DB is current.
/usr/local/bin/kestrel-bootstrap

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
