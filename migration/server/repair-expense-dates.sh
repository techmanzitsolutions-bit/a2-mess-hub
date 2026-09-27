#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
DB=techmanz-postgres
DBNAME=a2mess_staging
DBUSER=techmanz_admin
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/expense-date-repair-$STAMP"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - EXPENSE DATE / LEGACY TIMESTAMP REPAIR"
echo "============================================================"

mkdir -p "$BACKUP"
docker exec "$DB" pg_dump -U "$DBUSER" -d "$DBNAME" | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "Fresh PostgreSQL backup created"

docker exec -i "$DB" psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME" <<'SQL'
BEGIN;

-- Final Firebase export used Firestore timestamp wrapper objects.
-- Convert them to plain ISO strings so the TECH MANZ adapter and reports can
-- read them consistently, while preserving the original date/time exactly.
UPDATE live_documents
SET data=jsonb_set(data,'{createdAt}',to_jsonb(data->'createdAt'->>'__a2Timestamp'),true),
    updated_at=NOW()
WHERE collection='expenses'
  AND jsonb_typeof(data->'createdAt')='object'
  AND COALESCE(data->'createdAt'->>'__a2Timestamp','')<>'';

UPDATE live_documents
SET data=jsonb_set(data,'{updatedAt}',to_jsonb(data->'updatedAt'->>'__a2Timestamp'),true),
    updated_at=NOW()
WHERE collection='expenses'
  AND jsonb_typeof(data->'updatedAt')='object'
  AND COALESCE(data->'updatedAt'->>'__a2Timestamp','')<>'';

-- A migrated expense must always have an Added Date. Only fall back to the
-- original updatedAt when createdAt is genuinely absent.
UPDATE live_documents
SET data=jsonb_set(data,'{createdAt}',data->'updatedAt',true),
    updated_at=NOW()
WHERE collection='expenses'
  AND COALESCE(data->>'createdAt','')=''
  AND COALESCE(data->>'updatedAt','')<>'';

COMMIT;
SQL

COUNT="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "SELECT count(*) FROM live_documents WHERE collection='expenses';")"
[[ "$COUNT" == "59" ]] || fail "Expected 59 expenses, got $COUNT"

MISSING="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*) FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'createdAt','')='';
")"
[[ "$MISSING" == "0" ]] || fail "$MISSING expenses still have no Added Date"

INVALID="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*) FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'createdAt','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T';
")"
[[ "$INVALID" == "0" ]] || fail "$INVALID expense dates are not ISO timestamps"

# Check the exact records visible in the reported screen against the final
# Firebase export.
CHECK="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF '|' -c "
SELECT doc_id,data->>'createdAt',COALESCE(data->>'paymentMethod','')
FROM live_documents
WHERE collection='expenses'
  AND doc_id IN ('4wRWwPnMuHBvf913A06V','5ILxqY3f9PILhlG2toRE','6MCumwbfgJzT4asQX4ag')
ORDER BY doc_id;
")"

echo "$CHECK"

grep -q "4wRWwPnMuHBvf913A06V|2026-09-13T17:08:00.280Z|" <<<"$CHECK"   || fail "BANIYAS SPIKE AED 15 date does not match final Firebase export"
grep -q "5ILxqY3f9PILhlG2toRE|2026-09-25T15:07:19.233Z|CASH" <<<"$CHECK"   || fail "ROYAL EMIRATES AED 33.23 date/method mismatch"
grep -q "6MCumwbfgJzT4asQX4ag|2026-09-23T18:01:00.980Z|CASH" <<<"$CHECK"   || fail "ROYAL EMIRATES AED 85.01 date/method mismatch"

ok "All 59 expense Added Dates repaired/verified"
ok "Reported BANIYAS/ROYAL EMIRATES dates match the final Firebase export"

# Historical method coverage is reported, not invented.
WITH_METHOD="$(docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*) FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'paymentMethod','')<>'';
")"
WITHOUT_METHOD=$((59-WITH_METHOD))
echo "INFO: Payment method recorded: $WITH_METHOD / 59"
echo "INFO: Legacy expenses without payment method: $WITHOUT_METHOD / 59"
[[ "$WITH_METHOD" == "23" ]] || fail "Expected 23 expenses with historically recorded payment method, got $WITH_METHOD"

echo
echo "============================================================"
echo " EXPENSE DATE REPAIR PASSED"
echo " Expenses: 59"
echo " Added Dates present: 59 / 59"
echo " Historical payment methods recorded: 23 / 59"
echo " Legacy method-not-recorded entries: 36 / 59"
echo " Backup: $BACKUP"
echo "============================================================"
