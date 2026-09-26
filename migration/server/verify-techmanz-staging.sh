#!/usr/bin/env bash
set -euo pipefail

API="${A2_API:-http://192.168.1.112:3100}"
WEB="${A2_WEB:-http://192.168.1.112:3200}"
DB_CONTAINER="${A2_DB_CONTAINER:-techmanz-postgres}"
DB_NAME="${A2_DB_NAME:-a2mess_staging}"
DB_USER="${A2_DB_USER:-techmanz_admin}"
ROOT="${A2_ROOT:-/srv/techmanz/a2-mess}"
TMP="$(mktemp -d)"
PASS=0
SKIP=0

say(){ printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
ok(){ PASS=$((PASS+1)); echo "PASS: $*"; }
skip(){ SKIP=$((SKIP+1)); echo "SKIP: $*"; }
fail(){ echo "FAIL: $*" >&2; exit 1; }

cleanup(){
  rm -rf "$TMP" 2>/dev/null || true
  if [[ -n "${CHEF_ID:-}" && -n "${CHEF_HASH:-}" ]]; then
    docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" \
      -c "UPDATE users SET password_hash='$CHEF_HASH',active='$CHEF_ACTIVE'::boolean WHERE id='$CHEF_ID'::uuid;" >/dev/null 2>&1 || true
  fi
  if [[ -n "${MEMBER_ID:-}" && -n "${MEMBER_HASH:-}" ]]; then
    docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" \
      -c "UPDATE users SET password_hash='$MEMBER_HASH',active='$MEMBER_ACTIVE'::boolean WHERE id='$MEMBER_ID'::uuid;" >/dev/null 2>&1 || true
    if [[ -n "${MEMBER_PROFILE_ACTIVE:-}" ]]; then
      docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" \
        -c "UPDATE members SET active='$MEMBER_PROFILE_ACTIVE'::boolean WHERE user_id='$MEMBER_ID'::uuid;" >/dev/null 2>&1 || true
    fi
  fi
  if [[ -n "${BILL_FILE_ID:-}" ]]; then rm -f "$ROOT/storage/bills/$BILL_FILE_ID" 2>/dev/null || true; fi
}
trap cleanup EXIT

http_code(){
  local method="$1" url="$2" token="${3:-}" data="${4:-}"
  local args=(-sS -o "$TMP/body" -w '%{http_code}' -X "$method")
  [[ -n "$token" ]] && args+=(-H "Authorization: Bearer $token")
  [[ -n "$data" ]] && args+=(-H 'Content-Type: application/json' --data-binary "$data")
  curl "${args[@]}" "$url"
}
expect_code(){
  local want="$1" got="$2" label="$3"
  [[ "$got" == "$want" ]] || { echo "--- response ---"; cat "$TMP/body" || true; echo; fail "$label expected HTTP $want, got $got"; }
  ok "$label"
}
make_hash(){
  local pw="$1"
  PW="$pw" python3 - <<'PY'
import os,hashlib,secrets
p=os.environ["PW"].encode()
s=secrets.token_bytes(16)
d=hashlib.pbkdf2_hmac("sha256",p,s,600000)
print("pbkdf2_sha256$600000$"+s.hex()+"$"+d.hex())
PY
}

say "1/10 Runtime and frontend"
curl -fsS "$API/health" > "$TMP/health.json" || fail "API health"
python3 - "$TMP/health.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d.get("status")=="ok" and d.get("database")=="connected",d
PY
ok "API health + PostgreSQL connection"

curl -fsS "$API/openapi.json" > "$TMP/openapi.json" || fail "OpenAPI"
grep -q '"/compat/docs/{collection}"' "$TMP/openapi.json" || fail "Compatibility API not registered"
ok "Compatibility API registered"

curl -fsS "$WEB/app.html" > "$TMP/app.html" || fail "Frontend"
grep -q 'TECH MANZ server' "$TMP/app.html" || fail "TECH MANZ frontend marker missing"
grep -q 'techmanz-compat.js' "$TMP/app.html" || fail "Local compatibility adapter missing"
if grep -Eq 'www\.gstatic\.com/firebasejs|api\.cloudinary\.com|ucarecdn\.com' "$TMP/app.html"; then fail "External Firebase/Cloudinary/Uploadcare runtime remains"; fi
for marker in 'Total Receivable' 'monthlyClosings' 'mealSkips' 'Kitchen Meal Count' 'selectMemberPlan' 'ACCOUNT_TRANSFER'; do
  grep -q "$marker" "$TMP/app.html" || fail "Live feature marker missing: $marker"
done
ok "Exact live-derived frontend + critical feature markers"

say "2/10 Administrator authentication"
ADMIN_EMAIL="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "SELECT email FROM users WHERE role='admin' AND active=TRUE AND email IS NOT NULL ORDER BY created_at LIMIT 1;")"
[[ -n "$ADMIN_EMAIL" ]] || fail "Active administrator email not found"
printf 'Administrator: %s\n' "$ADMIN_EMAIL"
read -rsp "Enter current A2 admin password (hidden): " ADMIN_PASS
echo
LOGIN_JSON="$(ADMIN_EMAIL="$ADMIN_EMAIL" ADMIN_PASS="$ADMIN_PASS" python3 - <<'PY'
import os,json
print(json.dumps({"email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASS"]}))
PY
)"
CODE="$(http_code POST "$API/auth/login" "" "$LOGIN_JSON")"
expect_code 200 "$CODE" "Admin login"
ADMIN_TOKEN="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["access_token"])')"
unset ADMIN_PASS LOGIN_JSON
CODE="$(http_code GET "$API/admin/test" "$ADMIN_TOKEN")"
expect_code 200 "$CODE" "Admin authorization"

say "3/10 Compatibility collections"
for c in system users members inventory meals mealSkips expenses payments monthlyClosings settings notifications pushTokens; do
  CODE="$(http_code GET "$API/compat/docs/$c" "$ADMIN_TOKEN")"
  expect_code 200 "$CODE" "Admin reads $c"
done

say "4/10 Non-destructive compatibility writes"
STAMP="$(date +%s)"
for spec in \
  "inventory|{\"name\":\"__VERIFY_STOCK_$STAMP\",\"qty\":1,\"unit\":\"KG\",\"min\":0}" \
  "meals|{\"slot\":\"Lunch\",\"date\":\"2099-01-01\",\"menu\":\"__VERIFY_MEAL_$STAMP\"}" \
  "expenses|{\"title\":\"__VERIFY_EXPENSE_$STAMP\",\"amount\":1,\"category\":\"Verification\",\"paymentMethod\":\"CASH\"}" \
  "payments|{\"uid\":\"verification\",\"name\":\"Verification\",\"billingMonth\":\"2099-01\",\"planAmount\":100,\"paidAmount\":1,\"amount\":1,\"status\":\"PARTIAL\",\"paymentMethod\":\"CASH\"}" \
  "monthlyClosings|{\"month\":\"2099-01\",\"status\":\"CLOSED\",\"memberCount\":0,\"totalExpense\":0,\"members\":[]}"
do
  C="${spec%%|*}"; DATA="${spec#*|}"
  CODE="$(http_code POST "$API/compat/docs/$C" "$ADMIN_TOKEN" "$DATA")"
  expect_code 200 "$CODE" "Create temporary $C document"
  ID="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["id"])')"
  CODE="$(http_code DELETE "$API/compat/docs/$C/$ID" "$ADMIN_TOKEN")"
  expect_code 200 "$CODE" "Delete temporary $C document"
done

say "5/10 Month plan + carry field semantics"
DATA="{\"name\":\"__VERIFY_MEMBER_$STAMP\",\"phone\":\"\",\"joinDate\":\"2099-01-01\",\"plan\":\"AED 200\",\"planAmount\":200,\"planByMonth\":{\"2099-02\":250},\"manualCarryByMonth\":{\"2099-02\":35},\"active\":true}"
CODE="$(http_code POST "$API/compat/docs/members" "$ADMIN_TOKEN" "$DATA")"
expect_code 200 "$CODE" "Create temporary member with month plan/carry"
VERIFY_MEMBER_DOC="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["id"])')"
CODE="$(http_code GET "$API/compat/docs/members/$VERIFY_MEMBER_DOC" "$ADMIN_TOKEN")"
expect_code 200 "$CODE" "Read month plan/carry"
python3 - "$TMP/body" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))["data"]
assert d["planByMonth"]["2099-02"]==250,d
assert d["manualCarryByMonth"]["2099-02"]==35,d
PY
ok "Month-specific plan + carry values preserved"
CODE="$(http_code DELETE "$API/compat/docs/members/$VERIFY_MEMBER_DOC" "$ADMIN_TOKEN")"
expect_code 200 "$CODE" "Remove temporary member"

say "6/10 Chef role"
CHEF_ROW="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -AtF '|' -c "SELECT id,email,password_hash,active FROM users WHERE role='chef' AND email IS NOT NULL ORDER BY created_at LIMIT 1;")"
if [[ -n "$CHEF_ROW" ]]; then
  IFS='|' read -r CHEF_ID CHEF_EMAIL CHEF_HASH CHEF_ACTIVE <<< "$CHEF_ROW"
  CHEF_PASS="TmVerify!Chef$STAMP"
  CHEF_TEST_HASH="$(make_hash "$CHEF_PASS")"
  docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" -c "UPDATE users SET password_hash='$CHEF_TEST_HASH',active=TRUE WHERE id='$CHEF_ID'::uuid;" >/dev/null
  PAYLOAD="$(E="$CHEF_EMAIL" P="$CHEF_PASS" python3 - <<'PY'
import os,json
print(json.dumps({"email":os.environ["E"],"password":os.environ["P"]}))
PY
)"
  CODE="$(http_code POST "$API/auth/login" "" "$PAYLOAD")"; expect_code 200 "$CODE" "Chef login"
  CHEF_TOKEN="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["access_token"])')"
  CODE="$(http_code GET "$API/chef/test" "$CHEF_TOKEN")"; expect_code 200 "$CODE" "Chef permission"
  CODE="$(http_code GET "$API/admin/test" "$CHEF_TOKEN")"; expect_code 403 "$CODE" "Chef blocked from Admin"
  CODE="$(http_code GET "$API/compat/docs/expenses" "$CHEF_TOKEN")"; expect_code 200 "$CODE" "Chef reads expenses"
  CODE="$(http_code GET "$API/compat/docs/users" "$CHEF_TOKEN")"; expect_code 403 "$CODE" "Chef blocked from user directory"
else
  skip "No Chef staging account available"
fi

say "7/10 Member role"
MEMBER_ROW="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -AtF '|' -c "SELECT id,email,password_hash,active FROM users WHERE role='member' AND email IS NOT NULL ORDER BY created_at LIMIT 1;")"
if [[ -n "$MEMBER_ROW" ]]; then
  IFS='|' read -r MEMBER_ID MEMBER_EMAIL MEMBER_HASH MEMBER_ACTIVE <<< "$MEMBER_ROW"
  MEMBER_PROFILE_ACTIVE="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "SELECT active FROM members WHERE user_id='$MEMBER_ID'::uuid LIMIT 1;" || true)"
  MEMBER_PASS="TmVerify!Member$STAMP"
  MEMBER_TEST_HASH="$(make_hash "$MEMBER_PASS")"
  docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" -c "UPDATE users SET password_hash='$MEMBER_TEST_HASH',active=TRUE WHERE id='$MEMBER_ID'::uuid; UPDATE members SET active=TRUE WHERE user_id='$MEMBER_ID'::uuid;" >/dev/null
  PAYLOAD="$(E="$MEMBER_EMAIL" P="$MEMBER_PASS" python3 - <<'PY'
import os,json
print(json.dumps({"email":os.environ["E"],"password":os.environ["P"]}))
PY
)"
  CODE="$(http_code POST "$API/auth/login" "" "$PAYLOAD")"; expect_code 200 "$CODE" "Member login"
  MEMBER_TOKEN="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["access_token"])')"
  CODE="$(http_code GET "$API/member/test" "$MEMBER_TOKEN")"; expect_code 200 "$CODE" "Member permission"
  CODE="$(http_code GET "$API/admin/test" "$MEMBER_TOKEN")"; expect_code 403 "$CODE" "Member blocked from Admin"
  CODE="$(http_code GET "$API/chef/test" "$MEMBER_TOKEN")"; expect_code 403 "$CODE" "Member blocked from Chef"
  CODE="$(http_code GET "$API/compat/docs/payments" "$MEMBER_TOKEN")"; expect_code 200 "$CODE" "Member reads own payments"
  CODE="$(http_code GET "$API/compat/docs/users" "$MEMBER_TOKEN")"; expect_code 403 "$CODE" "Member blocked from user directory"

  TOMORROW="$(date -d tomorrow +%F)"
  CUTOFF="$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%SZ)"
  DATA="$(UIDV="$MEMBER_ID" D="$TOMORROW" C="$CUTOFF" python3 - <<'PY'
import os,json
print(json.dumps({"uid":os.environ["UIDV"],"memberId":"","memberName":"Verification Member","date":os.environ["D"],"meal":"Lunch","status":"SKIPPED","cutoffAt":os.environ["C"]}))
PY
)"
  CODE="$(http_code POST "$API/compat/docs/mealSkips" "$MEMBER_TOKEN" "$DATA")"; expect_code 200 "$CODE" "Member creates meal skip"
  SKIP_ID="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["id"])')"
  CODE="$(http_code DELETE "$API/compat/docs/mealSkips/$SKIP_ID" "$MEMBER_TOKEN")"; expect_code 200 "$CODE" "Member cancels meal skip before cutoff"
else
  skip "No Member staging account available"
fi

say "8/10 Local bill storage"
if [[ -n "${CHEF_TOKEN:-}" ]]; then
  python3 - "$TMP/test.png" <<'PY'
import base64,sys
open(sys.argv[1],"wb").write(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="))
PY
  CODE="$(curl -sS -o "$TMP/body" -w '%{http_code}' -H "Authorization: Bearer $CHEF_TOKEN" -F "bill=@$TMP/test.png;type=image/png" "$API/compat/files/bills")"
  expect_code 200 "$CODE" "Chef uploads bill to local storage"
  BILL_FILE_ID="$(python3 -c 'import json;print(json.load(open("'"$TMP/body"'"))["billFileId"])')"
  CODE="$(curl -sS -o "$TMP/bill.out" -w '%{http_code}' "$API/compat/files/bills/$BILL_FILE_ID")"
  expect_code 200 "$CODE" "Local bill can be viewed"
  [[ -f "$ROOT/storage/bills/$BILL_FILE_ID" ]] || fail "Bill not stored under TECH MANZ storage"
  rm -f "$ROOT/storage/bills/$BILL_FILE_ID"; BILL_FILE_ID=""
  ok "Temporary bill cleaned up"
else
  skip "Bill role test skipped because Chef account unavailable"
fi

say "9/10 Database and migration integrity"
for name in 010_live_documents_compat 011_seed_compat_from_staging; do
  N="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "SELECT count(*) FROM migration_log WHERE migration_name='$name';")"
  [[ "$N" == "1" ]] || fail "Migration missing or duplicated: $name"
done
ok "Compatibility migrations recorded once"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "SELECT count(*) FROM live_documents;" > "$TMP/doccount"
[[ "$(cat "$TMP/doccount")" =~ ^[0-9]+$ ]] || fail "live_documents count unavailable"
ok "Compatibility document store healthy ($(cat "$TMP/doccount") docs)"

say "10/10 External runtime dependency check"
if grep -RIEq 'www\.gstatic\.com/firebasejs|api\.cloudinary\.com|ucarecdn\.com' "$ROOT/app"; then fail "External runtime dependency found in deployed app"; fi
ok "No Firebase/Cloudinary/Uploadcare runtime dependency in deployed app"

echo
echo "============================================================"
echo " A2 MESS HUB FULL STAGING VALIDATION PASSED"
echo " Tests passed: $PASS"
echo " Tests skipped: $SKIP"
echo " URL: $WEB"
echo " Chef/Member passwords and active states restored after validation."
echo " Production GitHub Pages/Firebase were not modified."
echo "============================================================"
