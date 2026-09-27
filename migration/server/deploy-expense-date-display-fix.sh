#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/expense-date-display-$STAMP"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - EXPENSE DATE DISPLAY FIX"
echo "============================================================"

mkdir -p "$BACKUP/app"
cp -a "$ROOT/app/." "$BACKUP/app/"
ok "Current frontend backed up"

bash "$HERE/server/repair-expense-dates.sh"

python3 "$HERE/scripts/convert_generated_live.py"   "$HERE/generated-live"   "$HERE/techmanz-build"   "$HERE/frontend/techmanz-compat.js"

python3 "$HERE/scripts/local-parity-hardening.py"   "$HERE/techmanz-build/app.html"

grep -q "function a2Date(v)" "$HERE/techmanz-build/app.html" || fail "Robust date parser missing"
grep -q "Added Date" "$HERE/techmanz-build/app.html" || fail "Added Date column missing"
grep -q "techmanz-expense-date-20260927" "$HERE/techmanz-build/sw.js" || fail "Fresh cache marker missing"

TMP="$ROOT/app/.expense-date-next"
rm -rf "$TMP"
mkdir -p "$TMP"
cp -a "$HERE/techmanz-build/." "$TMP/"
find "$ROOT/app" -mindepth 1 -maxdepth 1 ! -name '.expense-date-next' -exec rm -rf {} +
cp -a "$TMP/." "$ROOT/app/"
rm -rf "$TMP"

docker compose -f "$ROOT/web/compose.yml" up -d
ok "Updated frontend installed"

curl -fsS http://127.0.0.1:3200/app.html | grep -q "function a2Date(v)" || fail "Local frontend is stale"
curl -fsS http://127.0.0.1:3200/sw.js | grep -q "techmanz-expense-date-20260927" || fail "Local service worker is stale"

PUBLIC_URL="$(tailscale funnel status 2>/dev/null | grep -Eo 'https://[^ /]+\.ts\.net' | head -1 || true)"
[[ -n "$PUBLIC_URL" ]] || fail "Public Funnel URL not detected"
curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/app.html?datefix=20260927" | grep -q "function a2Date(v)" || fail "Public frontend is stale"

echo
echo "============================================================"
echo " EXPENSE DATE DISPLAY FIX PASSED"
echo " Database dates: repaired/verified"
echo " Frontend date parser: updated"
echo " Added Date column: present"
echo " Public URL: $PUBLIC_URL"
echo " Backup: $BACKUP"
echo "============================================================"
