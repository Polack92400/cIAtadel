#!/bin/sh
set -eu
exec celery -A config worker --loglevel "${LOG_LEVEL:-INFO}" \
  --concurrency "${CELERY_CONCURRENCY:-2}" --hostname "worker@%h"
