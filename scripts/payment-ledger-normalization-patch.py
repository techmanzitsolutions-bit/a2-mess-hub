from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

OLD_PAID="function paidValue(x){const n=Number(x?.paidAmount??x?.amount??0);return Number.isFinite(n)?n:0}"
NEW_PAID="function paidValue(x){const raw=(x?.amount!==undefined&&x?.amount!==null&&x?.amount!=='')?x.amount:x?.paidAmount;const n=Number(raw??0);return Number.isFinite(n)?n:0}"
OLD_MONTH="function paymentMonth(p){return String(p?.billingMonth||timestampMonth(p?.createdAt)||timestampMonth(p?.updatedAt)||currentBillingMonth())}"
NEW_MONTH="function paymentMonth(p){return String(p?.billingMonth||timestampMonth(p?.createdAt)||timestampMonth(p?.updatedAt)||'')}"

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    if OLD_PAID in s:
        s=s.replace(OLD_PAID,NEW_PAID,1)
    elif NEW_PAID not in s:
        raise SystemExit('paidValue helper not found')
    if OLD_MONTH in s:
        s=s.replace(OLD_MONTH,NEW_MONTH,1)
    elif NEW_MONTH not in s:
        raise SystemExit('paymentMonth helper not found')
    if NEW_PAID not in s or NEW_MONTH not in s:
        raise SystemExit('Payment ledger normalization missing')
    app.write_text(s)
    print('Normalized payment totals: explicit transaction amount first; undated records excluded from month totals')
