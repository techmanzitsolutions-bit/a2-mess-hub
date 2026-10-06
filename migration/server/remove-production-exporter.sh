#!/usr/bin/env bash
set -euo pipefail
rm -f /srv/techmanz/a2-mess/app/production-exporter.html
if curl -fsS http://192.168.1.112:3200/production-exporter.html 2>/dev/null | grep -q 'Production Export'; then
  echo "FAIL: exporter still reachable"
  exit 1
fi
echo "PRODUCTION EXPORTER REMOVED"
