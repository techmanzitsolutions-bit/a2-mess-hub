#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/consolidation-$STAMP"

say(){ printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
fail(){ echo "FAIL: $*" >&2; exit 1; }

[ -d "$ROOT/api/app" ] || fail "A2 API directory not found"
[ -d "$HERE/techmanz-build" ] || fail "Generated TECH MANZ frontend build missing"
[ -f "$HERE/server/compat_api.py" ] || fail "compat_api.py missing"

say "Backing up current staging application"
mkdir -p "$BACKUP/api-app" "$BACKUP/web-app"
cp -a "$ROOT/api/app/." "$BACKUP/api-app/"
cp -a "$ROOT/app/." "$BACKUP/web-app/"
docker exec techmanz-postgres pg_dump -U techmanz_admin -d a2mess_staging | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"

say "Installing compatibility API"
cp "$HERE/server/compat_api.py" "$ROOT/api/app/compat_api.py"
python3 - <<'PY'
from pathlib import Path
p=Path('/srv/techmanz/a2-mess/api/app/meals.py')
s=p.read_text()
bad='from datetime import (\nimport json\n    date,'
if bad in s:
    s=s.replace(bad,'import json\n\nfrom datetime import (\n    date,',1)
p.write_text(s)

p=Path('/srv/techmanz/a2-mess/api/app/main.py')
s=p.read_text()
s=s.replace('TOKEN_MINUTES = 30','TOKEN_MINUTES = 10080',1)
marker='# TECH MANZ LIVE COMPATIBILITY ROUTER'
block='''\n\n# TECH MANZ LIVE COMPATIBILITY ROUTER\nfrom compat_api import create_compat_router\napp.include_router(create_compat_router(db, current_user, allow_roles, hash_password))\n'''
if marker not in s:
    s += block
p.write_text(s)
PY

python3 -m py_compile "$ROOT/api/app/main.py" "$ROOT/api/app/meals.py" "$ROOT/api/app/compat_api.py"

say "Applying PostgreSQL compatibility schema"
docker exec -i techmanz-postgres psql -v ON_ERROR_STOP=1 -U techmanz_admin -d a2mess_staging < "$HERE/server/010_live_documents.sql"
docker exec -i techmanz-postgres psql -v ON_ERROR_STOP=1 -U techmanz_admin -d a2mess_staging < "$HERE/server/011_seed_compat_from_staging.sql"

say "Installing exact live-derived frontend build"
rm -rf "$ROOT/app/.next-techmanz"
mkdir -p "$ROOT/app/.next-techmanz"
cp -a "$HERE/techmanz-build/." "$ROOT/app/.next-techmanz/"
rm -rf "$ROOT/app"/*
cp -a "$ROOT/app/.next-techmanz/." "$ROOT/app/"
rm -rf "$ROOT/app/.next-techmanz"

say "Rebuilding API and refreshing web container"
docker compose -f "$ROOT/api/compose.yml" up -d --build
docker compose -f "$ROOT/web/compose.yml" up -d

say "Waiting for API"
for i in $(seq 1 30); do
  if curl -fsS http://192.168.1.112:3100/health >/tmp/a2-health.json 2>/dev/null; then break; fi
  sleep 2
done
curl -fsS http://192.168.1.112:3100/health >/tmp/a2-health.json || fail "API health failed"
curl -fsS http://192.168.1.112:3100/openapi.json | grep -q '"/compat/docs/{collection}"' || fail "Compatibility API missing"
curl -fsS http://192.168.1.112:3200/app.html >/tmp/a2-app.html || fail "Frontend unavailable"
if grep -Eq 'www\.gstatic\.com/firebasejs|api\.cloudinary\.com|ucarecdn\.com' /tmp/a2-app.html; then fail "External Firebase/Cloudinary runtime reference remains"; fi
grep -q 'TECH MANZ server' /tmp/a2-app.html || fail "TECH MANZ converted frontend marker missing"

echo
echo "============================================================"
echo " A2 MESS HUB CONSOLIDATED STAGING BUILD PASSED"
echo " URL: http://192.168.1.112:3200"
echo " Backup: $BACKUP"
echo " Production Firebase/GitHub Pages were not modified."
echo "============================================================"
