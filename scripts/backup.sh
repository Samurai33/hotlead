#!/usr/bin/env bash
# HotLead — PostgreSQL backup with retention.
# Usage: ./scripts/backup.sh   (run from the repo root on the host)
# Cron:  0 3 * * * cd /path/to/hotlead && ./scripts/backup.sh >> backups/backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_USER="${POSTGRES_USER:-hotlead}"
POSTGRES_DB="${POSTGRES_DB:-hotlead}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="${BACKUP_DIR}/hotlead_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Is)] Starting backup → ${OUTFILE}"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner --no-privileges | gzip > "$OUTFILE"

# Sanity check: fail loudly on empty/tiny dumps
SIZE=$(stat -c%s "$OUTFILE" 2>/dev/null || stat -f%z "$OUTFILE")
if [ "$SIZE" -lt 1024 ]; then
  echo "[$(date -Is)] ERROR: backup suspiciously small (${SIZE} bytes)" >&2
  exit 1
fi

echo "[$(date -Is)] Backup OK (${SIZE} bytes). Pruning older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "hotlead_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "[$(date -Is)] Done."
