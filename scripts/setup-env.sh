#!/usr/bin/env sh
# Create .env from .env.example, replacing every `change-me` with a random
# secret. Refuses to overwrite an existing .env.
set -eu
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists - leaving it untouched."
  exit 0
fi

gen() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 40; }
kms() { printf 'ciatadel-key:%s' "$(head -c 32 /dev/urandom | base64 | tr -d '\n')"; }

: > .env
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    *=change-me-kms) printf '%s=%s\n' "${line%%=*}" "$(kms)" >> .env ;;
    *=change-me) printf '%s=%s\n' "${line%%=*}" "$(gen)" >> .env ;;
    *) printf '%s\n' "$line" >> .env ;;
  esac
done < .env.example
chmod 600 .env
echo ".env created with random secrets."
