#!/usr/bin/env bash
set -euo pipefail
ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/production-exporter.html"
DST="$ROOT/app/production-exporter.html"
[ -f "$SRC" ] || { echo "FAIL: exporter file missing"; exit 1; }
cp "$SRC" "$DST"
chmod 644 "$DST"
curl -fsS http://192.168.1.112:3200/production-exporter.html | grep -q 'Production Export'
echo
echo "============================================================"
echo " PRODUCTION EXPORTER READY"
echo " URL: http://192.168.1.112:3200/production-exporter.html"
echo " Read-only: Firebase is not modified."
echo "============================================================"
