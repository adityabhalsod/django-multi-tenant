#!/bin/sh
# Streaming read replica for local development (compose profile "replica").
# On first start it clones the primary with pg_basebackup, then follows it.
set -eu
export PGPASSWORD="$POSTGRES_REPLICATION_PASSWORD"

until pg_isready -h "$PRIMARY_HOST" -p 5432 -q; do
  echo "Waiting for primary $PRIMARY_HOST..."; sleep 1
done

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Cloning primary into $PGDATA"
  mkdir -p "$PGDATA" && chmod 700 "$PGDATA"
  # Create the replication slot only if the primary does not have it yet
  # (it survives when just the replica volume is deleted).
  SLOT_EXISTS=$(psql -h "$PRIMARY_HOST" -U replicator -d postgres -tAc \
    "SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_1'")
  CREATE_SLOT="--create-slot"
  [ "$SLOT_EXISTS" = "1" ] && CREATE_SLOT=""
  # shellcheck disable=SC2086
  pg_basebackup -h "$PRIMARY_HOST" -U replicator -D "$PGDATA" \
    --write-recovery-conf --wal-method=stream $CREATE_SLOT --slot=replica_1
fi

exec postgres -c hot_standby=on
