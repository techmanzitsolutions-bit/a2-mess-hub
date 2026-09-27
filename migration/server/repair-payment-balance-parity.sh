#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
DB=techmanz-postgres
DBNAME=a2mess_staging
DBUSER=techmanz_admin
MONTH=2026-09
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/backups/payment-balance-parity-$STAMP"
REPORT="$BACKUP/member-balances.tsv"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - PAYMENT / BALANCE PARITY REPAIR"
echo " Source: final Firebase export 2026-09-27T10:14:56.018Z"
echo " Month: $MONTH"
echo "============================================================"

mkdir -p "$BACKUP"
docker exec "$DB" pg_dump -U "$DBUSER" -d "$DBNAME" | gzip -9 > "$BACKUP/a2mess_staging.sql.gz"
ok "Fresh PostgreSQL backup created"

# The legacy Firebase app allowed old payment documents without billingMonth.
# Its UI inferred the month from createdAt. Make that inference explicit in
# the local copy so paid/due calculations are deterministic.
docker exec -i "$DB" psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME" <<'SQL'
BEGIN;

UPDATE live_documents
SET data = jsonb_set(
      data,
      '{billingMonth}',
      to_jsonb(substr(COALESCE(NULLIF(data->>'createdAt',''),NULLIF(data->>'updatedAt','')),1,7)),
      true
    ),
    updated_at = NOW()
WHERE collection='payments'
  AND COALESCE(data->>'billingMonth','')=''
  AND COALESCE(NULLIF(data->>'createdAt',''),NULLIF(data->>'updatedAt','')) ~ '^[0-9]{4}-[0-9]{2}';

COMMIT;
SQL
ok "Legacy payment months normalized"

# Verify the specific fully-paid HAKKIM transaction from Firebase.
HAKKIM="$(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -Atc "
SELECT count(*)
FROM live_documents
WHERE collection='payments'
  AND doc_id='GTxgBZTMB1D1TsmH12wx'
  AND data->>'billingMonth'='$MONTH'
  AND round(COALESCE((data->>'amount')::numeric,(data->>'paidAmount')::numeric,0),2)=200.00
  AND upper(COALESCE(data->>'status',''))='PAID';
"
)"
[[ "$HAKKIM" == "1" ]] || fail "HAKKIM AED 200 paid transaction is not correctly recognized"
ok "HAKKIM AED 200 fully-paid transaction recognized"

# Reconcile the member snapshot fields from the authoritative payment ledger.
docker exec -i "$DB" psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME" <<'SQL'
WITH members AS (
  SELECT
    doc_id,
    data,
    COALESCE(NULLIF(data->>'uid',''),doc_id) AS member_key,
    COALESCE(
      NULLIF(data->'planByMonth'->>'2026-09','')::numeric,
      NULLIF(data->>'planAmount','')::numeric,
      0
    ) AS plan,
    COALESCE(
      NULLIF(data->'manualCarryByMonth'->>'2026-09','')::numeric,
      CASE WHEN data->>'carryToMonth'='2026-09'
           THEN COALESCE(NULLIF(data->>'carryBalance','')::numeric,0)
           ELSE 0 END,
      0
    ) AS opening
  FROM live_documents
  WHERE collection='members'
),
payments AS (
  SELECT
    COALESCE(data->>'uid','') AS member_key,
    SUM(COALESCE(NULLIF(data->>'amount','')::numeric,
                 NULLIF(data->>'paidAmount','')::numeric,0)) AS paid
  FROM live_documents
  WHERE collection='payments'
    AND data->>'billingMonth'='2026-09'
  GROUP BY COALESCE(data->>'uid','')
),
calc AS (
  SELECT
    m.doc_id,
    m.plan,
    m.opening,
    COALESCE(p.paid,0) AS paid,
    GREATEST(m.plan-(m.opening+COALESCE(p.paid,0)),0) AS due,
    GREATEST((m.opening+COALESCE(p.paid,0))-m.plan,0) AS advance,
    CASE
      WHEN GREATEST((m.opening+COALESCE(p.paid,0))-m.plan,0) > 0.005 THEN 'ADVANCE'
      WHEN GREATEST(m.plan-(m.opening+COALESCE(p.paid,0)),0) <= 0.005 THEN 'PAID'
      WHEN (m.opening+COALESCE(p.paid,0)) > 0.005 THEN 'PARTIAL'
      ELSE 'DUE'
    END AS status
  FROM members m
  LEFT JOIN payments p ON p.member_key=m.member_key
)
UPDATE live_documents ld
SET data =
    jsonb_set(
      jsonb_set(
        jsonb_set(
          jsonb_set(
            jsonb_set(ld.data,'{currentBillingMonth}',to_jsonb('2026-09'::text),true),
            '{paidAmount}',to_jsonb(round(c.paid,2)),true
          ),
          '{dueAmount}',to_jsonb(round(c.due,2)),true
        ),
        '{advanceAmount}',to_jsonb(round(c.advance,2)),true
      ),
      '{status}',to_jsonb(c.status),true
    ),
    updated_at=NOW()
FROM calc c
WHERE ld.collection='members'
  AND ld.doc_id=c.doc_id;
SQL
ok "Member paid/due/status snapshots reconciled"

docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF $'\t' -c "
WITH members AS (
  SELECT
    doc_id,
    data->>'name' AS name,
    COALESCE(NULLIF(data->'planByMonth'->>'$MONTH','')::numeric,
             NULLIF(data->>'planAmount','')::numeric,0) AS plan,
    COALESCE(NULLIF(data->>'paidAmount','')::numeric,0) AS paid,
    COALESCE(NULLIF(data->>'dueAmount','')::numeric,0) AS due,
    COALESCE(NULLIF(data->>'advanceAmount','')::numeric,0) AS advance,
    COALESCE(data->>'status','') AS status
  FROM live_documents
  WHERE collection='members'
)
SELECT name,round(plan,2),round(paid,2),round(due,2),round(advance,2),status
FROM members
ORDER BY name;
" > "$REPORT"

python3 - "$REPORT" <<'PY'
from decimal import Decimal
import sys

expected = {
    "MUMTAZAR": ("200.00","200.00","0.00","0.00","PAID"),
    "Ajith": ("200.00","200.00","0.00","0.00","PAID"),
    "HAKKIM": ("200.00","200.00","0.00","0.00","PAID"),
    "JEFIN PETER": ("200.00","130.00","70.00","0.00","PARTIAL"),
    "VICKY": ("100.00","100.00","0.00","0.00","PAID"),
    "AL THAF": ("200.00","200.00","0.00","0.00","PAID"),
    "SAHAL": ("200.00","200.00","0.00","0.00","PAID"),
    "RASHEED": ("200.00","200.00","0.00","0.00","PAID"),
    "SHAJI": ("200.00","151.13","48.87","0.00","PARTIAL"),
    "ALI": ("200.00","165.00","35.00","0.00","PARTIAL"),
    "SAFUAN": ("200.00","200.00","0.00","0.00","PAID"),
}

def q(v):
    return f"{Decimal(v):.2f}"

got={}
for line in open(sys.argv[1],encoding="utf-8"):
    line=line.rstrip("\n")
    if not line: continue
    name,plan,paid,due,advance,status=line.split("\t")
    got[name]=(q(plan),q(paid),q(due),q(advance),status)

missing=set(expected)-set(got)
extra=set(got)-set(expected)
bad={k:(expected[k],got.get(k)) for k in expected if got.get(k)!=expected[k]}
if missing or extra or bad:
    print("Balance parity mismatch")
    if missing: print("Missing:",sorted(missing))
    if extra: print("Extra:",sorted(extra))
    for k,v in bad.items(): print(k,"expected",v[0],"got",v[1])
    raise SystemExit(1)

print("member-parity-ok")
PY
ok "All 11 member paid/due/status values match final Firebase"

read -r RECEIVABLE COLLECTED DUE PAID_COUNT PARTIAL_COUNT DUE_COUNT < <(
docker exec "$DB" psql -U "$DBUSER" -d "$DBNAME" -AtF ' ' -c "
SELECT
  round(sum(COALESCE(NULLIF(data->'planByMonth'->>'$MONTH','')::numeric,
                         NULLIF(data->>'planAmount','')::numeric,0)),2),
  round(sum(COALESCE(NULLIF(data->>'paidAmount','')::numeric,0)),2),
  round(sum(COALESCE(NULLIF(data->>'dueAmount','')::numeric,0)),2),
  count(*) FILTER (WHERE data->>'status'='PAID'),
  count(*) FILTER (WHERE data->>'status'='PARTIAL'),
  count(*) FILTER (WHERE data->>'status'='DUE')
FROM live_documents
WHERE collection='members';
"
)

[[ "$RECEIVABLE" == "2100.00" ]] || fail "Receivable mismatch: $RECEIVABLE"
[[ "$COLLECTED" == "1946.13" ]] || fail "Collected mismatch: $COLLECTED"
[[ "$DUE" == "153.87" ]] || fail "Due mismatch: $DUE"
[[ "$PAID_COUNT" == "8" ]] || fail "Fully-paid member count mismatch: $PAID_COUNT"
[[ "$PARTIAL_COUNT" == "3" ]] || fail "Partial member count mismatch: $PARTIAL_COUNT"
[[ "$DUE_COUNT" == "0" ]] || fail "No-payment due member count mismatch: $DUE_COUNT"

ok "Dashboard totals: receivable AED 2100.00 / collected AED 1946.13 / due AED 153.87"
ok "Member statuses: 8 PAID / 3 PARTIAL / 0 DUE"

echo
printf '%-18s %10s %10s %10s %10s %s\n' "MEMBER" "PLAN" "PAID" "DUE" "ADVANCE" "STATUS"
while IFS=$'\t' read -r n p paid due adv st; do
  printf '%-18s %10s %10s %10s %10s %s\n' "$n" "$p" "$paid" "$due" "$adv" "$st"
done < "$REPORT"

echo
echo "============================================================"
echo " PAYMENT / BALANCE PARITY PASSED"
echo " Receivable: AED 2100.00"
echo " Collected:  AED 1946.13"
echo " Balance Due: AED 153.87"
echo " Fully Paid: 8"
echo " Partial:    3"
echo " Due/Unpaid: 0"
echo " Backup: $BACKUP"
echo "============================================================"
