#!/usr/bin/env bash
# HotLead — PostgreSQL backup with retention.
#
# Works in two environments:
#   - Local/dev:  ./scripts/backup.sh                (uses docker compose)
#   - Coolify VM: CONTAINER_FILTER=postgres-<uuid> ./scripts/backup.sh
#     (Coolify names containers <service>-<resource-uuid>-<ts>; there is no
#      compose project on the host, so we locate the container by name filter)
#
# Cron on the Coolify VM (daily 03:00, keep the uuid out of the repo):
#   0 3 * * * BACKUP_DIR=/var/backups/hotlead CONTAINER_FILTER=postgres-<uuid> \
#     /opt/hotlead-backup.sh >> /var/backups/hotlead/backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_USER="${POSTGRES_USER:-hotlead}"
POSTGRES_DB="${POSTGRES_DB:-hotlead}"
CONTAINER_FILTER="${CONTAINER_FILTER:-}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="${BACKUP_DIR}/hotlead_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"
echo "[$(date -Is)] Starting backup → ${OUTFILE}"

if [ -n "$CONTAINER_FILTER" ]; then
  CID="$(docker ps -qf "name=${CONTAINER_FILTER}" | head -n1)"
  if [ -z "$CID" ]; then
    echo "[$(date -Is)] ERROR: no running container matches name filter '${CONTAINER_FILTER}'" >&2
    exit 1
  fi
  docker exec "$CID" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --no-owner --no-privileges | gzip > "$OUTFILE"
else
  docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --no-owner --no-privileges | gzip > "$OUTFILE"
fi

# Sanity check: fail loudly on empty/tiny dumps
SIZE=$(stat -c%s "$OUTFILE" 2>/dev/null || stat -f%z "$OUTFILE")
if [ "$SIZE" -lt 1024 ]; then
  echo "[$(date -Is)] ERROR: backup suspiciously small (${SIZE} bytes)" >&2
  exit 1
fi

echo "[$(date -Is)] Backup OK (${SIZE} bytes). Pruning older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "hotlead_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "[$(date -Is)] Done."
