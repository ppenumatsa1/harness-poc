#!/bin/sh
# Create random local DB passwords in ./secrets (git-ignored). Existing files are kept.
# Rotate an app password: delete its file, run this script, then `docker compose up -d`.
set -eu
cd "$(dirname "$0")"
mkdir -p secrets && chmod 700 secrets
for name in postgres_password app_ro_password app_rw_password; do
  f="secrets/$name"
  if [ ! -s "$f" ]; then
    # hex: no quotes or special characters to escape in DSNs
    openssl rand -hex 24 > "$f"
    echo "created $f"
  fi
  chmod 644 "$f"  # containers run as other users (postgres, app); the 700 folder protects them on the host
done
