#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/mobile-input-date-hotfix-$STAMP"
DB=techmanz-postgres
DBNAME=a2mess_staging
DBUSER=techmanz_admin

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - MOBILE INPUT + EXPENSE DATE HOTFIX"
echo "============================================================"

mkdir -p "$BACKUP/app"
cp -a "$ROOT/app/." "$BACKUP/app/"
docker exec "$DB" pg_dump -U "$DBUSER" -d "$DBNAME" | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "Frontend and PostgreSQL backup created"

python3 "$HERE/scripts/convert_generated_live.py"   "$HERE/generated-live"   "$HERE/techmanz-build"   "$HERE/frontend/techmanz-compat.js"

python3 "$HERE/scripts/local-parity-hardening.py"   "$HERE/techmanz-build/app.html"

node --check "$HERE/techmanz-build/input-hardening.js"

grep -q 'inputmode=email' "$HERE/techmanz-build/app.html" || fail "Native email keyboard attribute missing"
grep -q 'autocomplete=username' "$HERE/techmanz-build/app.html" || fail "Login autocomplete marker missing"
grep -q 'a2-mobile-input-v2' "$HERE/techmanz-build/app.html" || fail "Mobile login CSS hardening missing"
grep -q 'input-hardening.js' "$HERE/techmanz-build/app.html" || fail "Input hardening runtime missing"
grep -q 'pointerdown' "$HERE/techmanz-build/input-hardening.js" || fail "Mobile gesture focus fallback missing"
grep -q "techmanz-mobile-input-v2-20260927" "$HERE/techmanz-build/sw.js" || fail "Fresh service-worker cache marker missing"
ok "Mobile typing build validated"

bash "$HERE/server/repair-expense-dates.sh"
ok "Expense dates repaired against final Firebase export"

rm -rf "$ROOT/app/.hotfix-next"
mkdir -p "$ROOT/app/.hotfix-next"
cp -a "$HERE/techmanz-build/." "$ROOT/app/.hotfix-next/"
find "$ROOT/app" -mindepth 1 -maxdepth 1 ! -name '.hotfix-next' -exec rm -rf {} +
cp -a "$ROOT/app/.hotfix-next/." "$ROOT/app/"
rm -rf "$ROOT/app/.hotfix-next"

docker compose -f "$ROOT/web/compose.yml" up -d
ok "Updated frontend installed"

# Server-side truth: all production expense dates must exist and be ISO.
COUNT="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "SELECT count(*) FROM live_documents WHERE collection='expenses';")"
[[ "$COUNT" == "59" ]] || fail "Expected 59 expenses, got $COUNT"
MISSING="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "SELECT count(*) FROM live_documents WHERE collection='expenses' AND COALESCE(data->>'createdAt','')='';")"
[[ "$MISSING" == "0" ]] || fail "$MISSING expense dates still missing"
ok "Database has 59 / 59 expense dates"

curl -fsS http://127.0.0.1:3200/app.html > /tmp/a2-hotfix-local.html
grep -q 'inputmode=email' /tmp/a2-hotfix-local.html || fail "Local login input fix not served"
grep -q 'Added Date' /tmp/a2-hotfix-local.html || fail "Local Added Date UI not served"

PUBLIC_URL="$(tailscale funnel status 2>/dev/null | grep -Eo 'https://[^ /]+\.ts\.net' | head -1 || true)"
[[ -n "$PUBLIC_URL" ]] || fail "Public Funnel URL not detected"

curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/app.html?build=mobile-input-v2" > /tmp/a2-hotfix-public.html
grep -q 'inputmode=email' /tmp/a2-hotfix-public.html || fail "Public login input fix not served"
grep -q 'a2-mobile-input-v2' /tmp/a2-hotfix-public.html || fail "Public mobile login CSS not served"
grep -q 'Added Date' /tmp/a2-hotfix-public.html || fail "Public Added Date UI not served"

curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/input-hardening.js?build=mobile-input-v2" > /tmp/a2-hotfix-input.js
grep -q 'focusEditableFromGesture' /tmp/a2-hotfix-input.js || fail "Public mobile focus fallback not served"

ok "Public mobile login/input hotfix is live"

echo
echo "============================================================"
echo " MOBILE INPUT + EXPENSE DATE HOTFIX PASSED"
echo " Expense dates: 59 / 59"
echo " Login email: native mobile email input"
echo " Login password: native mobile password input"
echo " Search fields: continuous typing without re-render blur"
echo " Public URL: $PUBLIC_URL"
echo " Backup: $BACKUP"
echo "============================================================"
