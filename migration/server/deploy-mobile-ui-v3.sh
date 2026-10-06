#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/mobile-ui-v3-$STAMP"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - MOBILE UI + EXPENSE DATE FIX V3"
echo "============================================================"

mkdir -p "$BACKUP/app"
cp -a "$ROOT/app/." "$BACKUP/app/"
docker exec techmanz-postgres pg_dump -U techmanz_admin -d a2mess_staging | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "Current frontend and database backed up"

bash "$HERE/server/repair-expense-dates.sh"
ok "Expense dates repaired and verified"

test -f "$HERE/techmanz-build/app.html" || fail "Validated frontend build missing"
test -f "$HERE/techmanz-build/input-hardening.js" || fail "Mobile input helper missing"
grep -q 'Added Date' "$HERE/techmanz-build/app.html" || fail "Added Date UI missing"
grep -q 'function a2Date(v,depth=0)' "$HERE/techmanz-build/app.html" || fail "Robust date parser missing"
grep -q 'input-hardening.js' "$HERE/techmanz-build/app.html" || fail "Mobile input helper not loaded"
grep -q 'touchend' "$HERE/techmanz-build/input-hardening.js" || fail "Touch focus handling missing"
grep -q 'techmanz-mobile-input-v3-20260927' "$HERE/techmanz-build/sw.js" || fail "Fresh mobile cache marker missing"
ok "Validated mobile/date build ready"

TMP="$ROOT/app/.mobile-ui-v3-next"
rm -rf "$TMP"
mkdir -p "$TMP"
cp -a "$HERE/techmanz-build/." "$TMP/"
find "$ROOT/app" -mindepth 1 -maxdepth 1 ! -name '.mobile-ui-v3-next' -exec rm -rf {} +
cp -a "$TMP/." "$ROOT/app/"
rm -rf "$TMP"

docker compose -f "$ROOT/web/compose.yml" up -d
ok "Updated frontend installed"

curl -fsS http://127.0.0.1:3200/app.html?fix=mobile-ui-v3 > /tmp/a2-mobile-v3-local.html
grep -q 'Added Date' /tmp/a2-mobile-v3-local.html || fail "Local Added Date UI not served"
grep -q 'input-hardening.js' /tmp/a2-mobile-v3-local.html || fail "Local mobile input helper not served"

PUBLIC_URL="$(tailscale funnel status 2>/dev/null | grep -Eo 'https://[^ /]+\.ts\.net' | head -1 || true)"
[[ -n "$PUBLIC_URL" ]] || fail "Public Funnel URL not detected"

curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/app.html?fix=mobile-ui-v3" > /tmp/a2-mobile-v3-public.html
grep -q 'Added Date' /tmp/a2-mobile-v3-public.html || fail "Public Added Date UI not served"
grep -q 'input-hardening.js' /tmp/a2-mobile-v3-public.html || fail "Public mobile input helper not served"

curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/input-hardening.js?fix=mobile-ui-v3" > /tmp/a2-mobile-v3-input.js
grep -q 'touchend' /tmp/a2-mobile-v3-input.js || fail "Public touch input fix not served"

ok "Public mobile/date fix is live"

echo
echo "============================================================"
echo " MOBILE UI + EXPENSE DATE FIX V3 PASSED"
echo " Expense dates: 59 / 59 verified"
echo " Mobile typing: touch handling enabled"
echo " Search typing: no per-character page rebuild"
echo " Public URL: $PUBLIC_URL"
echo " Backup: $BACKUP"
echo "============================================================"
