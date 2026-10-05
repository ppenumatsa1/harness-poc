#!/bin/bash
# Least-privilege roles (Lesson 6 idea, applied to data):
#   app_ro : read everything (agent read tools, API lists)
#   app_rw : read everything + write ONLY the fixes table (propose_fix / apply_fix)
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v ro_pw="$APP_RO_PASSWORD" -v rw_pw="$APP_RW_PASSWORD" <<'SQL'
CREATE ROLE app_ro LOGIN PASSWORD :'ro_pw';
CREATE ROLE app_rw LOGIN PASSWORD :'rw_pw';
GRANT CONNECT ON DATABASE checkout TO app_ro, app_rw;
GRANT USAGE ON SCHEMA public TO app_ro, app_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_ro, app_rw;
GRANT INSERT, UPDATE ON fixes TO app_rw;
GRANT USAGE ON SEQUENCE fixes_id_seq TO app_rw;
SQL
