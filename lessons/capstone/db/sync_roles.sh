#!/bin/sh
# db-roles service: runs on every `docker compose up`, after db is healthy.
# Sets the app role passwords from the secret files, so changing a file + `up` rotates it.
# The superuser password is the exception: this script logs in with it, so changing it needs `down -v`.
set -eu
export PGPASSWORD="$(cat /run/secrets/postgres_password)"
psql -v ON_ERROR_STOP=1 -h db -U postgres -d checkout \
  -v ro_pw="$(cat /run/secrets/app_ro_password)" -v rw_pw="$(cat /run/secrets/app_rw_password)" <<'SQL'
ALTER ROLE app_ro PASSWORD :'ro_pw';
ALTER ROLE app_rw PASSWORD :'rw_pw';
SQL
echo "app role passwords synced"
