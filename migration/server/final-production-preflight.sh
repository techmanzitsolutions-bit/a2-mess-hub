#!/usr/bin/env bash
set -euo pipefail

API="${A2_API:-http://192.168.1.112:3100}"
WEB="${A2_WEB:-http://192.168.1.112:3200}"
DB_CONTAINER="${A2_DB_CONTAINER:-techmanz-postgres}"
DB_NAME="${A2_DB_NAME:-a2mess_staging}"
DB_USER="${A2_DB_USER:-techmanz_admin}"
ROOT="${A2_ROOT:-/srv/techmanz/a2-mess}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/backups/production-preflight-$STAMP"
mkdir -p "$OUT"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - FINAL PRODUCTION DATA PREFLIGHT"
echo "============================================================"

curl -fsS "$API/health" > "$OUT/health.json" || fail "API health"
python3 - "$OUT/health.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d.get("status")=="ok" and d.get("database")=="connected",d
PY
ok "API health and PostgreSQL"

curl -fsS "$WEB/app.html" > "$OUT/app.html" || fail "Frontend unavailable"
grep -q 'TECH MANZ server' "$OUT/app.html" || fail "TECH MANZ frontend marker missing"
if grep -Eq 'www\.gstatic\.com/firebasejs|api\.cloudinary\.com|ucarecdn\.com' "$OUT/app.html"; then
  fail "External runtime dependency remains in app.html"
fi
ok "TECH MANZ frontend has no Firebase/Cloudinary/Uploadcare runtime dependency"

docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip -9 > "$OUT/a2mess_staging.sql.gz"
ok "Fresh PostgreSQL preflight backup created"

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -AtF '|' > "$OUT/live-doc-summary.txt" <<'SQL'
WITH c AS (
  SELECT collection,count(*)::int n
  FROM live_documents
  GROUP BY collection
)
SELECT collection,n FROM c ORDER BY collection;
SQL

python3 - "$OUT/live-doc-summary.txt" <<'PY'
import sys
expected={
 "users":12,"members":11,"inventory":0,"meals":2,"mealSkips":5,
 "expenses":58,"payments":29,"monthlyClosings":1,"settings":0,
 "notifications":0,"system":1
}
got={}
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    k,v=line.split("|",1);got[k]=int(v)
for k,v in expected.items():
    if got.get(k,0)!=v:
        raise SystemExit(f"{k}: expected {v}, got {got.get(k,0)}")
print("counts-ok")
PY
ok "Production document counts match reviewed export"

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At > "$OUT/financials.txt" <<'SQL'
SELECT
  COALESCE((SELECT round(sum(COALESCE((data->>'amount')::numeric,(data->>'paidAmount')::numeric,0)),2)
            FROM live_documents WHERE collection='payments'),0),
  COALESCE((SELECT round(sum(COALESCE((data->>'amount')::numeric,0)),2)
            FROM live_documents WHERE collection='expenses'),0);
SQL

FIN="$(cat "$OUT/financials.txt")"
[[ "$FIN" == "2890.13|1570.18" ]] || fail "Financial totals mismatch: $FIN"
ok "Payments AED 2890.13 and expenses AED 1570.18 match reviewed export"

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At > "$OUT/roles.txt" <<'SQL'
SELECT COALESCE(data->>'role',''),count(*)
FROM live_documents
WHERE collection='users'
GROUP BY 1
ORDER BY 1;
SQL

python3 - "$OUT/roles.txt" <<'PY'
import sys
got={}
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    k,v=line.split("|",1);got[k]=int(v)
expected={"admin":1,"chef":1,"member":10}
if got!=expected:
    raise SystemExit(f"role counts mismatch: {got}")
PY
ok "User roles match production: 1 Admin, 1 Chef, 10 Members"

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At > "$OUT/bills.txt" <<'SQL'
SELECT
  count(*) FILTER (WHERE COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'),
  count(*) FILTER (WHERE COALESCE(data->>'billUrl','') ~ '^https?://'),
  count(*) FILTER (WHERE COALESCE(data->>'billUrl','') = '')
FROM live_documents
WHERE collection='expenses';
SQL

BILLS="$(cat "$OUT/bills.txt")"
[[ "$BILLS" == "47|0|11" ]] || fail "Bill migration mismatch (local|external|empty): $BILLS"
ok "47 bill images local, 0 external URLs, 11 expenses without bill images"

MISSING="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At <<'SQL'
SELECT count(*)
FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'
  AND NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_class
    WHERE false
  );
SQL
)"
# Verify actual files directly from JSON file names.
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At <<'SQL' > "$OUT/bill-files.txt"
SELECT data->>'billFileId'
FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'
ORDER BY 1;
SQL
while IFS= read -r f; do
  [[ -n "$f" ]] || continue
  [[ -f "$ROOT/storage/bills/$f" ]] || fail "Missing local bill file: $f"
done < "$OUT/bill-files.txt"
ok "All referenced local bill files exist on disk"

# Ensure production user documents are linked to local UUID-like auth IDs.
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At > "$OUT/user-link-check.txt" <<'SQL'
SELECT count(*)
FROM live_documents
WHERE collection='users'
  AND doc_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  AND COALESCE(data->>'uid','')=doc_id;
SQL
[[ "$(cat "$OUT/user-link-check.txt")" == "12" ]] || fail "Not all production users are mapped to TECH MANZ local IDs"
ok "All 12 production user profiles mapped to TECH MANZ local IDs"

# Keep the original production snapshot files and backups, but remove temporary browser migration tools.
rm -f "$ROOT/app/production-exporter.html" "$ROOT/app/production-importer.html"
if curl -fsS "$WEB/production-importer.html" 2>/dev/null | grep -q 'Production → TECH MANZ Import'; then
  fail "Temporary importer page is still reachable"
fi
ok "Temporary migration pages removed"

cat > "$OUT/RESULT.txt" <<EOF
A2 MESS HUB FINAL PRODUCTION DATA PREFLIGHT PASSED
Timestamp: $STAMP
Users: 12
Members: 11
Payments: 29 / AED 2890.13
Expenses: 58 / AED 1570.18
Meals: 2
Meal skips: 5
Monthly closings: 1
Bill images local: 47
External bill URLs: 0
Runtime Firebase/Cloudinary/Uploadcare: 0
EOF

echo
echo "============================================================"
echo " A2 MESS HUB FINAL PRODUCTION DATA PREFLIGHT PASSED"
echo " Backup/report: $OUT"
echo " Staging URL: $WEB"
echo " Production Firebase remains untouched."
echo "============================================================"
