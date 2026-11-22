#!/bin/sh
# Runs once, when the PostgreSQL volume is first initialised.
# 1. Creates the extra databases listed in POSTGRES_EXTRA_DATABASES.
# 2. Creates a replication role + pg_hba rule used by the optional replica.
set -eu

for db in $(echo "${POSTGRES_EXTRA_DATABASES:-}" | tr ',' ' '); do
  echo "Creating extra database: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -c "CREATE DATABASE \"$db\" OWNER \"$POSTGRES_USER\";"
done

if [ -n "${POSTGRES_REPLICATION_PASSWORD:-}" ]; then
  echo "Creating replication role"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -c "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '${POSTGRES_REPLICATION_PASSWORD}';"
  echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
fi
