#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
DB=techmanz-postgres
DBNAME=a2mess_staging
DBUSER=techmanz_admin
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/expense-date-normalize-$STAMP"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - EXPENSE DATE NORMALIZATION"
echo "============================================================"

mkdir -p "$BACKUP"
docker exec "$DB" pg_dump -U "$DBUSER" -d "$DBNAME" | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "Fresh PostgreSQL backup created"

docker exec -i "$DB" psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME" <<'SQL'
BEGIN;

UPDATE live_documents
SET data=jsonb_set(
          data,
          '{createdAt}',
          to_jsonb(data->'createdAt'->>'__a2Timestamp'),
          true
        ),
    updated_at=NOW()
WHERE collection='expenses'
  AND jsonb_typeof(data->'createdAt')='object'
  AND COALESCE(data->'createdAt'->>'__a2Timestamp','')<>'';

UPDATE live_documents
SET data=jsonb_set(
          data,
          '{updatedAt}',
          to_jsonb(data->'updatedAt'->>'__a2Timestamp'),
          true
        ),
    updated_at=NOW()
WHERE collection='expenses'
  AND jsonb_typeof(data->'updatedAt')='object'
  AND COALESCE(data->'updatedAt'->>'__a2Timestamp','')<>'';

UPDATE live_documents
SET data=jsonb_set(data,'{createdAt}',data->'updatedAt',true),
    updated_at=NOW()
WHERE collection='expenses'
  AND COALESCE(data->>'createdAt','')=''
  AND COALESCE(data->>'updatedAt','')<>'';

COMMIT;
SQL

read -r TOTAL GOOD BAD < <(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF ' ' -c "
SELECT
  count(*),
  count(*) FILTER (
    WHERE jsonb_typeof(data->'createdAt')='string'
      AND data->>'createdAt' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
  ),
  count(*) FILTER (
    WHERE NOT (
      jsonb_typeof(data->'createdAt')='string'
      AND data->>'createdAt' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
    )
  )
FROM live_documents
WHERE collection='expenses';
"
)

[[ "$TOTAL" == "59" ]] || fail "Expected 59 expenses, got $TOTAL"
[[ "$GOOD" == "59" ]] || fail "Only $GOOD/59 expense dates normalized"
[[ "$BAD" == "0" ]] || fail "$BAD expense dates remain invalid"

ok "All 59 expense createdAt values are valid ISO timestamps"

echo
echo "Sample migrated records:"
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF '|' -c "
SELECT data->>'title',data->>'amount',data->>'createdAt'
FROM live_documents
WHERE collection='expenses'
  AND data->>'title' IN ('BANIYAS SPIKE SUPERMARKET','ROYAL EMIRATES SUPERMARKET')
ORDER BY data->>'createdAt' DESC
LIMIT 8;
"

echo
echo "============================================================"
echo " EXPENSE DATE NORMALIZATION PASSED"
echo " 59 / 59 dates ready for display"
echo " Backup: $BACKUP"
echo "============================================================"
