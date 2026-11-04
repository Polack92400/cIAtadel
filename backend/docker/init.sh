#!/bin/sh
# One-shot initialisation: migrations (as the owner role), bucket, demo data.
set -eu

echo "[init] applying migrations as the schema owner"
DATABASE_URL="$MIGRATION_DATABASE_URL" python manage.py migrate --noinput

echo "[init] ensuring the storage bucket exists"
python manage.py init_storage

if [ "${SEED_DEMO:-true}" = "true" ]; then
  echo "[init] seeding demo firms, users and documents"
  python manage.py seed_demo
fi
echo "[init] done"
