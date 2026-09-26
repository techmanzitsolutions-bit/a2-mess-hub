#!/usr/bin/env bash
set -euo pipefail

ROOT="${A2_ROOT:-/srv/techmanz/a2-mess}"
DB_CONTAINER="${A2_DB_CONTAINER:-techmanz-postgres}"
DB_NAME="${A2_DB_NAME:-a2mess_staging}"
DB_USER="${A2_DB_USER:-techmanz_admin}"
BILL_DIR="$ROOT/storage/bills"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT="$ROOT/backups/bill-repair-$STAMP"
mkdir -p "$REPORT" "$BILL_DIR"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - PRODUCTION BILL STORAGE REPAIR"
echo "============================================================"

docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip -9 > "$REPORT/a2mess_staging.sql.gz"
ok "Fresh PostgreSQL backup created"

docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -AtF $'\t' > "$REPORT/bill-map.tsv" <<'SQL'
SELECT
  doc_id,
  COALESCE(data->>'billFileId',''),
  COALESCE(data->>'legacyBillUrl',''),
  COALESCE(data->>'billUrl','')
FROM live_documents
WHERE collection='expenses'
  AND COALESCE(data->>'billUrl','') LIKE '/api/compat/files/bills/%'
ORDER BY doc_id;
SQL

TOTAL="$(wc -l < "$REPORT/bill-map.tsv" | tr -d ' ')"
[[ "$TOTAL" == "47" ]] || fail "Expected 47 local bill references, found $TOTAL"
ok "47 local bill references found"

MISSING_BEFORE=0
REPAIRED=0
FAILED=0
: > "$REPORT/repaired.tsv"
: > "$REPORT/failed.tsv"

while IFS=$'\t' read -r DOC_ID FILE_ID LEGACY_URL BILL_URL; do
  [[ -n "$FILE_ID" ]] || { echo -e "$DOC_ID\tmissing-file-id\t$LEGACY_URL" >> "$REPORT/failed.tsv"; FAILED=$((FAILED+1)); continue; }
  TARGET="$BILL_DIR/$FILE_ID"
  if [[ -s "$TARGET" ]]; then
    continue
  fi

  MISSING_BEFORE=$((MISSING_BEFORE+1))
  echo "Repairing missing bill: $FILE_ID"

  case "$LEGACY_URL" in
    https://res.cloudinary.com/*) ;;
    *)
      echo -e "$DOC_ID\tinvalid-or-missing-legacy-url\t$LEGACY_URL" >> "$REPORT/failed.tsv"
      FAILED=$((FAILED+1))
      continue
      ;;
  esac

  TMP="$REPORT/$FILE_ID.part"
  if curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 90 \
      -A 'A2-MESS-HUB-Migration/1.0' \
      "$LEGACY_URL" -o "$TMP"; then
    if [[ ! -s "$TMP" ]]; then
      echo -e "$DOC_ID\tempty-download\t$LEGACY_URL" >> "$REPORT/failed.tsv"
      rm -f "$TMP"
      FAILED=$((FAILED+1))
      continue
    fi

    # Reject obvious HTML/XML error payloads even if the HTTP status was 200.
    MIME="$(file -b --mime-type "$TMP" 2>/dev/null || true)"
    case "$MIME" in
      image/jpeg|image/png|image/webp|image/gif|application/octet-stream) ;;
      *)
        echo -e "$DOC_ID\tunexpected-mime:$MIME\t$LEGACY_URL" >> "$REPORT/failed.tsv"
        rm -f "$TMP"
        FAILED=$((FAILED+1))
        continue
        ;;
    esac

    # The storage bind mount is owned for the API container (UID 10001),
    # not the interactive techmanz shell user. Copy through Docker so the
    # host user does not need write permission on /srv/techmanz/a2-mess/storage/bills.
    docker cp "$TMP" "a2mess-api:/data/bills/$FILE_ID"
    docker exec -u 0 a2mess-api chown 10001:10001 "/data/bills/$FILE_ID"
    docker exec -u 0 a2mess-api chmod 0644 "/data/bills/$FILE_ID"
    rm -f "$TMP"
    [[ -s "$TARGET" ]] || {
      echo -e "$DOC_ID\tdocker-copy-failed\t$LEGACY_URL" >> "$REPORT/failed.tsv"
      FAILED=$((FAILED+1))
      continue
    }
    echo -e "$DOC_ID\t$FILE_ID\t$LEGACY_URL" >> "$REPORT/repaired.tsv"
    REPAIRED=$((REPAIRED+1))
  else
    rm -f "$TMP"
    echo -e "$DOC_ID\tdownload-failed\t$LEGACY_URL" >> "$REPORT/failed.tsv"
    FAILED=$((FAILED+1))
  fi
done < "$REPORT/bill-map.tsv"

echo
echo "Missing before repair: $MISSING_BEFORE"
echo "Repaired: $REPAIRED"
echo "Failed: $FAILED"

# Full verification of every local bill reference.
MISSING_AFTER=0
: > "$REPORT/missing-after.tsv"
while IFS=$'\t' read -r DOC_ID FILE_ID LEGACY_URL BILL_URL; do
  if [[ -z "$FILE_ID" || ! -s "$BILL_DIR/$FILE_ID" ]]; then
    echo -e "$DOC_ID\t$FILE_ID\t$LEGACY_URL" >> "$REPORT/missing-after.tsv"
    MISSING_AFTER=$((MISSING_AFTER+1))
  fi
done < "$REPORT/bill-map.tsv"

[[ "$MISSING_AFTER" == "0" ]] || {
  echo
  echo "Bills still missing:"
  cat "$REPORT/missing-after.tsv"
  fail "$MISSING_AFTER local bill file(s) still missing"
}

ok "All 47 referenced bill files exist locally"

# Build integrity manifest.
while IFS=$'\t' read -r DOC_ID FILE_ID LEGACY_URL BILL_URL; do
  sha256sum "$BILL_DIR/$FILE_ID"
done < "$REPORT/bill-map.tsv" > "$REPORT/bill-sha256.txt"
ok "Bill checksum manifest created"

echo
echo "============================================================"
echo " BILL STORAGE REPAIR PASSED"
echo " Report: $REPORT"
echo "============================================================"

# Continue directly into the final production-data preflight.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$HERE/final-production-preflight.sh"
