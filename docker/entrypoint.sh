#!/bin/sh
# Container entrypoint: wait for dependencies, optionally migrate, then exec CMD.
#
#   WAIT_FOR_DB=1        (default) block until PostgreSQL accepts connections
#   RUN_MIGRATIONS=1     run migrate_schemas (+ extra DBs) and bootstrap_public
#
# Only ONE container (the web service, or a one-off job) should set
# RUN_MIGRATIONS=1, so that replicas of the web service don't race each other.
set -eu

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
  python - <<'PY'
import os, sys, time
import psycopg

url = os.environ["DATABASE_URL"]
deadline = time.monotonic() + int(os.environ.get("DB_WAIT_TIMEOUT", "60"))
while True:
    try:
        psycopg.connect(url, connect_timeout=3).close()
        break
    except psycopg.OperationalError as exc:
        if time.monotonic() > deadline:
            sys.exit(f"Database not reachable: {exc}")
        print("Waiting for database...", flush=True)
        time.sleep(1)
PY
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running migrations (public schema, then every tenant schema)..."
  python manage.py migrate_schemas --noinput
  python manage.py migrate_extra
  python manage.py bootstrap_public
fi

exec "$@"
