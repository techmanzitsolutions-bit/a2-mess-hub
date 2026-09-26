#!/usr/bin/env bash
set -euo pipefail
ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/pre-production-import-$STAMP"
mkdir -p "$BACKUP"
docker exec techmanz-postgres pg_dump -U techmanz_admin -d a2mess_staging | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
cp "$HERE/production-importer.html" "$ROOT/app/production-importer.html"
rm -f "$ROOT/app/production-exporter.html"
chmod 644 "$ROOT/app/production-importer.html"
curl -fsS http://192.168.1.112:3200/production-importer.html | grep -q 'Production → TECH MANZ Import'
echo
echo "============================================================"
echo " PRODUCTION IMPORTER READY"
echo " URL: http://192.168.1.112:3200/production-importer.html"
echo " PostgreSQL backup: $BACKUP"
echo " Firebase production remains read-only/untouched."
echo "============================================================"
