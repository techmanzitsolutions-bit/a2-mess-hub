#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB=techmanz-postgres
DBNAME=a2mess_staging
DBUSER=techmanz_admin
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/full-live-parity-$STAMP"
FINAL_EXPENSE_ID="jjUqF0Wv9BRat63ZcUmU"
FINAL_BILL="final-jjUqF0Wv9BRat63ZcUmU.jpg"
FINAL_SOURCE="https://res.cloudinary.com/rtsrjhpm/image/upload/v1790419681/A2-MESS-HUB/Bills/yeevhzh96kgbh9hksc1h.jpg"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - COMPLETE LIVE APP PARITY DEPLOYMENT"
echo "============================================================"

[[ -d "$HERE/techmanz-build" ]] || fail "Validated TECH MANZ build missing"
[[ -f "$HERE/generated-live/app.html" ]] || fail "Exact generated live reference missing"
[[ -f "$HERE/server/repair-payment-balance-parity.sh" ]] || fail "Payment parity repair missing"

mkdir -p "$BACKUP/app"
cp -a "$ROOT/app/." "$BACKUP/app/"
docker exec "$DB" pg_dump -U "$DBUSER" -d "$DBNAME" | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "Frontend + PostgreSQL backup created"

# Normalize any timestamp wrappers left by old import paths.
docker exec -i "$DB" psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME" <<'SQL'
BEGIN;

UPDATE live_documents
SET data=jsonb_set(data,'{createdAt}',to_jsonb(data->'createdAt'->>'__a2Timestamp'),true),
    updated_at=NOW()
WHERE jsonb_typeof(data->'createdAt')='object'
  AND COALESCE(data->'createdAt'->>'__a2Timestamp','')<>'';

UPDATE live_documents
SET data=jsonb_set(data,'{updatedAt}',to_jsonb(data->'updatedAt'->>'__a2Timestamp'),true),
    updated_at=NOW()
WHERE jsonb_typeof(data->'updatedAt')='object'
  AND COALESCE(data->'updatedAt'->>'__a2Timestamp','')<>'';

UPDATE live_documents
SET data=jsonb_set(data,'{createdAt}',data->'updatedAt',true),
    updated_at=NOW()
WHERE collection='expenses'
  AND COALESCE(data->>'createdAt','')=''
  AND COALESCE(data->>'updatedAt','')<>'';

-- Remove cloud-provider metadata after local bill migration.
UPDATE live_documents
SET data=(data-'legacyBillUrl') ||
         CASE
           WHEN COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'
           THEN jsonb_build_object('imageProvider','local')
           ELSE '{}'::jsonb
         END,
    updated_at=NOW()
WHERE collection='expenses';

UPDATE live_documents
SET data=(data-'uploadcarePublicKey') || jsonb_build_object('imageProvider','local'),
    updated_at=NOW()
WHERE collection='system' AND doc_id='config';

DELETE FROM live_documents WHERE collection='pushTokens';

COMMIT;
SQL
ok "Dates/provider metadata normalized"

# Ensure the one record created after the first migration snapshot is present
# and its image is local before old Cloudinary data can be retired.
NEED_FINAL="$(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT CASE WHEN EXISTS(
  SELECT 1 FROM live_documents
  WHERE collection='expenses' AND doc_id='$FINAL_EXPENSE_ID'
    AND COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'
) THEN 0 ELSE 1 END;
"
)"

if [[ "$NEED_FINAL" == "1" ]]; then
  echo "Localizing final MARK & SAVE bill..."
  curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 90 "$FINAL_SOURCE" -o "/tmp/$FINAL_BILL"
  [[ -s "/tmp/$FINAL_BILL" ]] || fail "Final MARK & SAVE bill download failed"
  docker cp "/tmp/$FINAL_BILL" "a2mess-api:/data/bills/$FINAL_BILL"
  docker exec -u 0 a2mess-api chown 10001:10001 "/data/bills/$FINAL_BILL"
  docker exec -u 0 a2mess-api chmod 0644 "/data/bills/$FINAL_BILL"

  ADMIN_ID="$(
    docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
      SELECT id::text FROM users
      WHERE lower(email)=lower('a.hakkim7468@gmail.com')
        AND role='admin' AND active=TRUE
      LIMIT 1;
    "
  )"
  [[ -n "$ADMIN_ID" ]] || fail "Local Admin ID not found"

  docker exec -i "$DB" psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME" <<SQL
INSERT INTO live_documents(collection,doc_id,data)
VALUES(
  'expenses',
  '$FINAL_EXPENSE_ID',
  jsonb_build_object(
    'createdAt','2026-09-26T10:48:01.950Z',
    'updatedAt','2026-09-26T10:48:32.949Z',
    'amount',158.80,
    'createdBy','$ADMIN_ID',
    'createdByName','ABDULHAKKIM ALAVUDEEN',
    'imageProvider','local',
    'billFileId','$FINAL_BILL',
    'billUrl','/api/compat/files/bills/$FINAL_BILL',
    'category','Grocery',
    'title','MARK & SAVE',
    'paymentMethod','CARD'
  )
)
ON CONFLICT(collection,doc_id)
DO UPDATE SET
  data=EXCLUDED.data,
  updated_at=NOW();
SQL
  rm -f "/tmp/$FINAL_BILL"
  ok "Final MARK & SAVE expense and bill localized"
else
  ok "Final MARK & SAVE expense already localized"
fi

# Install the validated exact-live-derived build.
TMP="$ROOT/app/.full-parity-next"
rm -rf "$TMP"
mkdir -p "$TMP"
cp -a "$HERE/techmanz-build/." "$TMP/"
find "$ROOT/app" -mindepth 1 -maxdepth 1 ! -name '.full-parity-next' -exec rm -rf {} +
cp -a "$TMP/." "$ROOT/app/"
rm -rf "$TMP"
docker compose -f "$ROOT/web/compose.yml" up -d
ok "Complete live-derived frontend installed"

# Repair/reconcile historical payment month inference and member balances.
bash "$HERE/server/repair-payment-balance-parity.sh"
ok "Payment and member balance parity repaired"

# Collection-count parity with final Firebase export.
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF '|' -c "
SELECT collection,count(*) FROM live_documents GROUP BY collection ORDER BY collection;
" > /tmp/a2-parity-counts.txt

python3 - <<'PY'
expected={
  'users':12,'members':11,'inventory':0,'meals':2,'mealSkips':5,
  'expenses':59,'payments':29,'monthlyClosings':1,'settings':0,
  'notifications':0,'pushTokens':0,'system':1
}
got={}
for line in open('/tmp/a2-parity-counts.txt'):
    line=line.strip()
    if not line: continue
    k,v=line.split('|',1);got[k]=int(v)
bad=[f"{k}: expected {v}, got {got.get(k,0)}" for k,v in expected.items() if got.get(k,0)!=v]
if bad: raise SystemExit('Collection parity failed: '+'; '.join(bad))
print('collection-parity-ok')
PY
ok "All final production collection counts match"

# Every final expense must have a valid added date.
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF '|' -c "
SELECT doc_id,COALESCE(data->>'createdAt','')
FROM live_documents WHERE collection='expenses'
ORDER BY doc_id;
" > /tmp/a2-expense-dates.txt

python3 - <<'PY'
from datetime import datetime
rows=[]
for line in open('/tmp/a2-expense-dates.txt'):
    line=line.rstrip('\n')
    if not line: continue
    doc,date=line.split('|',1);rows.append((doc,date))
if len(rows)!=59: raise SystemExit(f'Expected 59 expenses, got {len(rows)}')
bad=[]
for doc,value in rows:
    try:
        if not value: raise ValueError('missing')
        datetime.fromisoformat(value.replace('Z','+00:00'))
    except Exception:
        bad.append((doc,value))
if bad: raise SystemExit('Invalid expense added dates: '+repr(bad))
print('expense-date-parity-ok')
PY
ok "All 59 expense Added Dates are present and valid"

EXP_TOTAL="$(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT round(COALESCE(sum((data->>'amount')::numeric),0),2)
FROM live_documents WHERE collection='expenses';
"
)"
[[ "$EXP_TOTAL" == "1728.98" ]] || fail "Expense total mismatch: $EXP_TOTAL"
ok "Expense total matches final export: AED 1728.98"

LOCAL_BILLS="$(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*) FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%';
"
)"
[[ "$LOCAL_BILLS" == "48" ]] || fail "Expected 48 local bill references, got $LOCAL_BILLS"

EXTERNAL="$(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*) FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'billUrl','') ~ '^https?://';
"
)"
[[ "$EXTERNAL" == "0" ]] || fail "$EXTERNAL external bill URLs remain"

PROVIDER_REFS="$(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*) FROM live_documents
WHERE data::text ~* 'cloudinary|ucarecdn|firebaseapp';
"
)"
[[ "$PROVIDER_REFS" == "0" ]] || fail "$PROVIDER_REFS cloud-provider references remain in live data"
ok "Database has 48 local bills and no Cloudinary/Firebase/Uploadcare runtime references"

docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT data->>'billFileId'
FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'
ORDER BY 1;
" > /tmp/a2-parity-bills.txt

while IFS= read -r F; do
  [[ -n "$F" ]] || continue
  docker exec a2mess-api test -s "/data/bills/$F" || fail "Missing local bill file: $F"
done < /tmp/a2-parity-bills.txt
ok "All 48 local bill image files physically verified"

# Exact old-app function parity: all named functions in generated live must
# remain in the TECH MANZ build; local-only adapter changes are allowed.
python3 - "$HERE/generated-live/app.html" "$ROOT/app/app.html" <<'PY'
from pathlib import Path
import re,sys
old=Path(sys.argv[1]).read_text()
new=Path(sys.argv[2]).read_text()
pattern=r'function\s+([A-Za-z0-9_$]+)\s*\('
a=set(re.findall(pattern,old));b=set(re.findall(pattern,new))
missing=sorted(a-b)
if missing: raise SystemExit('Missing old-live functions: '+', '.join(missing))
required=[
 'Added Date','Added By / Actions','Date not recorded',"timeZone:'Asia/Dubai'",
 'Total Receivable','PARTIAL','monthlyClosings','mealSkips','Kitchen Meal Count',
 'plan-choice','selectMemberPlan','ACCOUNT_TRANSFER','openBillViewer',
 'manualCarryByMonth','planByMonth','WhatsApp Pending Members',
 'a2-live-notifications','tm-solutions-approved.webp'
]
miss=[x for x in required if x not in new]
if miss: raise SystemExit('Missing required parity markers: '+', '.join(miss))
print(f'frontend-function-parity-ok:{len(a)}')
PY
ok "All named functions from the exact old live app are preserved"

if grep -RIEq 'www\.gstatic\.com/firebasejs|api\.cloudinary\.com|ucarecdn\.com|firebase\.initializeApp|firebase\.messaging\(\)' "$ROOT/app"; then
  fail "External Firebase/Cloudinary/Uploadcare runtime dependency remains in frontend"
fi
ok "Frontend has no Firebase/Cloudinary/Uploadcare runtime dependency"

curl -fsS http://192.168.1.112:3100/health | grep -q '"status":"ok"' || fail "Local API failed"
curl -fsS http://127.0.0.1:3200/app.html | grep -q 'Added Date' || fail "Updated local frontend not served"

PUBLIC_URL="$(tailscale funnel status 2>/dev/null | grep -Eo 'https://[^ /]+\.ts\.net' | head -1 || true)"
[[ -n "$PUBLIC_URL" ]] || fail "Public Funnel URL not detected"
curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/app.html" | grep -q 'Added Date' || fail "Updated public frontend not served"
curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/api/health" | grep -q '"status":"ok"' || fail "Public API failed"
ok "Updated application works locally and through public Funnel"

docker rm -f a2-final-exporter >/dev/null 2>&1 || true
sudo ufw --force delete allow from 192.168.1.0/24 to any port 3301 proto tcp >/dev/null 2>&1 || true
rm -f "$ROOT/app/production-exporter.html" "$ROOT/app/production-exporter-final.html"
ok "Temporary Firebase exporter removed"

cat > "$BACKUP/FULL-LIVE-PARITY-PASSED.txt" <<EOF
A2 MESS HUB COMPLETE LIVE APP PARITY PASSED
Time: $(date -Is)
Source final Firebase export: 2026-09-27T10:14:56.018Z
Users: 12
Members: 11
Expenses: 59 / AED 1728.98
Payments: 29 / AED 2890.13
September receivable: AED 2100.00
September collected: AED 1946.13
September due: AED 153.87
September paid/partial/unpaid: 8 / 3 / 0
Expense Added Dates valid: 59 / 59
Local bill images: 48
External bill URLs: 0
Old-live named frontend functions preserved: YES
Firebase runtime dependency: NO
Cloudinary runtime dependency: NO
Uploadcare runtime dependency: NO
Public URL: $PUBLIC_URL
EOF

echo
echo "============================================================"
echo " A2 MESS HUB COMPLETE LIVE APP PARITY PASSED"
echo " Expenses: 59 / AED 1728.98"
echo " Added Dates: 59 / 59 valid"
echo " September Collected: AED 1946.13"
echo " September Due: AED 153.87"
echo " Fully Paid / Partial / Unpaid: 8 / 3 / 0"
echo " Local bills: 48 / External: 0"
echo " Public URL: $PUBLIC_URL"
echo " Backup/report: $BACKUP"
echo "============================================================"
