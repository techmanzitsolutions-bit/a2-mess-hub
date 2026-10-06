#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/final-ui-auth-repair-$STAMP"
API_COMPOSE="$ROOT/api/compose.yml"
API_APP="$ROOT/api/app"
WEB_APP="$ROOT/app"
SECRET_DIR="$ROOT/api/secrets"
SECRET_FILE="$SECRET_DIR/legacy_firebase_api_key"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - FINAL UI / DATE / LOGIN REPAIR"
echo "============================================================"

mkdir -p "$BACKUP/api-app" "$BACKUP/web-app"
cp -a "$API_APP/." "$BACKUP/api-app/"
cp -a "$WEB_APP/." "$BACKUP/web-app/"
cp -a "$API_COMPOSE" "$BACKUP/api-compose.yml"
docker exec techmanz-postgres pg_dump -U techmanz_admin -d a2mess_staging | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "API, frontend, compose and PostgreSQL backup created"

echo
echo "Building exact live-derived frontend with final hardening..."
python3 "$HERE/scripts/convert_generated_live.py" "$HERE/generated-live" "$HERE/techmanz-build" "$HERE/frontend/techmanz-compat.js"
python3 "$HERE/scripts/local-parity-hardening.py" "$HERE/techmanz-build/app.html"

grep -q 'input-hardening.js' "$HERE/techmanz-build/app.html" || fail "Input hardening missing from build"
grep -q 'Added Date' "$HERE/techmanz-build/app.html" || fail "Expense Added Date UI missing"
grep -q 'techmanz-final-ui-auth-20260927' "$HERE/techmanz-build/sw.js" || fail "Final service-worker marker missing"
! grep -q 'Firestore user profiles' "$HERE/techmanz-build/app.html" || fail "Firestore migration note still visible"
! grep -q 'local authentication passwords are never included' "$HERE/techmanz-build/app.html" || fail "Authentication migration note still visible"
ok "Clean final frontend built"

echo
echo "Restoring exact final expense dates/payment metadata..."
docker exec -i techmanz-postgres psql -v ON_ERROR_STOP=1 -U techmanz_admin -d a2mess_staging < "$HERE/server/sql/012_final_expense_metadata.sql"
docker exec -i techmanz-postgres psql -v ON_ERROR_STOP=1 -U techmanz_admin -d a2mess_staging < "$HERE/server/sql/013_legacy_auth_transition.sql"

DATE_COUNT="$(docker exec techmanz-postgres psql -U techmanz_admin -d a2mess_staging -Atc "
SELECT count(*)
FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'createdAt','') ~ '^2026-09-[0-9]{2}T';
")"
[[ "$DATE_COUNT" == "59" ]] || fail "Expected 59 expense dates, got $DATE_COUNT"
ok "All 59 original expense Added Dates restored"

echo
echo "Preparing temporary existing-password transition bridge..."
mkdir -p "$SECRET_DIR"
python3 - "$HERE/generated-live/app.html" "$BACKUP/legacy-key.tmp" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
m=re.search(r"apiKey:'([^']+)'",s)
if not m:
    raise SystemExit("Legacy Firebase public API key not found in generated live source")
Path(sys.argv[2]).write_text(m.group(1))
PY
sudo install -o 10001 -g 10001 -m 0400 "$BACKUP/legacy-key.tmp" "$SECRET_FILE"
rm -f "$BACKUP/legacy-key.tmp"

python3 - "$API_COMPOSE" "$SECRET_FILE" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
secret=sys.argv[2]
s=p.read_text()
target='/run/secrets/legacy_firebase_api_key'
if target not in s:
    lines=s.splitlines()
    out=[]
    inserted=False
    for line in lines:
        out.append(line)
        if '/run/secrets/jwt_secret' in line:
            indent=line[:len(line)-len(line.lstrip())]
            out.append(f'{indent}- "{secret}:{target}:ro"')
            inserted=True
    if not inserted:
        raise SystemExit("Could not locate API secret-volume section in compose.yml")
    p.write_text('\n'.join(out)+'\n')
PY
docker compose -f "$API_COMPOSE" config >/dev/null
ok "Temporary legacy password verifier mounted privately"

echo
echo "Installing backend login transition + clean frontend..."
cp "$HERE/server/compat_api.py" "$API_APP/compat_api.py"
python3 -m py_compile "$API_APP/compat_api.py" "$API_APP/main.py"

rm -rf "$WEB_APP/.next-final"
mkdir -p "$WEB_APP/.next-final"
cp -a "$HERE/techmanz-build/." "$WEB_APP/.next-final/"
find "$WEB_APP" -mindepth 1 -maxdepth 1 ! -name '.next-final' -exec rm -rf {} +
cp -a "$WEB_APP/.next-final/." "$WEB_APP/"
rm -rf "$WEB_APP/.next-final"

docker compose -f "$API_COMPOSE" up -d --build
docker compose -f "$ROOT/web/compose.yml" up -d

echo
echo "Waiting for services..."
for i in $(seq 1 30); do
  if curl -fsS http://192.168.1.112:3100/health >/tmp/a2-final-repair-health.json 2>/dev/null; then break; fi
  sleep 2
done
curl -fsS http://192.168.1.112:3100/health | grep -q '"status":"ok"' || fail "API health failed"
curl -fsS http://192.168.1.112:3100/openapi.json | grep -q '"/compat/auth/legacy-login"' || fail "Legacy password bridge endpoint missing"
curl -fsS http://127.0.0.1:3200/app.html | grep -q 'Added Date' || fail "Updated frontend not served"
curl -fsS http://127.0.0.1:3200/app.html | grep -q 'input-hardening.js' || fail "Typing hardening not served"
! curl -fsS http://127.0.0.1:3200/app.html | grep -q 'Firestore user profiles' || fail "Old Firestore note still served"
ok "API + clean frontend deployed"

echo
echo "Testing Admin login and reading password-transition status..."
ADMIN_EMAIL="$(docker exec techmanz-postgres psql -U techmanz_admin -d a2mess_staging -Atc "
SELECT email FROM users
WHERE role='admin' AND active=TRUE
ORDER BY created_at LIMIT 1;
")"
[[ -n "$ADMIN_EMAIL" ]] || fail "Active Admin not found"
echo "Admin: $ADMIN_EMAIL"
read -rsp "Enter current TECH MANZ Admin password (hidden): " ADMIN_PASS
echo
LOGIN_JSON="$(E="$ADMIN_EMAIL" P="$ADMIN_PASS" python3 - <<'PY'
import json,os
print(json.dumps({"email":os.environ["E"],"password":os.environ["P"]}))
PY
)"
HTTP="$(curl -sS -o /tmp/a2-final-admin-login.json -w '%{http_code}' -H 'Content-Type: application/json' --data-binary "$LOGIN_JSON" http://192.168.1.112:3100/auth/login)"
unset ADMIN_PASS LOGIN_JSON
[[ "$HTTP" == "200" ]] || fail "Admin login failed (HTTP $HTTP)"
TOKEN="$(python3 - <<'PY'
import json
print(json.load(open('/tmp/a2-final-admin-login.json'))['access_token'])
PY
)"
curl -fsS -H "Authorization: Bearer $TOKEN" http://192.168.1.112:3100/compat/auth/migration-status > /tmp/a2-auth-transition.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/a2-auth-transition.json'))
print(f"Active users: {d['active_users']}")
print(f"Existing passwords migrated locally: {d['migrated']}")
print(f"Still waiting for first login: {len(d['pending'])}")
for u in d['pending']:
    print("  PENDING:",u.get('name') or u.get('email'),"-",u.get('role'))
PY
ok "Existing-password transition status available"

PUBLIC_URL="$(tailscale funnel status 2>/dev/null | grep -Eo 'https://[^ /]+\.ts\.net' | head -1 || true)"
[[ -n "$PUBLIC_URL" ]] || fail "Public Funnel URL not detected"
curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/app.html" | grep -q 'input-hardening.js' || fail "Public frontend not updated"
curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/api/health" | grep -q '"status":"ok"' || fail "Public API failed"
ok "Public app updated"

echo
echo "============================================================"
echo " A2 FINAL UI / DATE / LOGIN REPAIR PASSED"
echo " Expense dates restored: 59 / 59"
echo " Mobile typing hardening: ACTIVE"
echo " Migration/Firestore notes: REMOVED"
echo " Existing user passwords: AUTO-MIGRATE ON FIRST LOGIN"
echo " Public URL: $PUBLIC_URL"
echo " Backup: $BACKUP"
echo "============================================================"
echo
echo "IMPORTANT:"
echo "Do NOT delete Firebase Authentication yet."
echo "Each old user should login once with the SAME old password."
echo "That first successful login copies the password into TECH MANZ local auth."
echo "After all active users are migrated, the legacy password bridge can be removed."
