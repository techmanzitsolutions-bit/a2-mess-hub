from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

REPORTS=r'''function reports(){
  const month=window._reportMonth||currentBillingMonth();
  const g=globalPaymentSummary(month);
  const total=Number(g.receivable||0);
  const paid=Number(g.received||0);
  const due=Number(g.balance||0);
  const ex=state.data.expenses.filter(x=>recordMonth(x)===month);
  const spent=ex.reduce((a,x)=>a+Number(x.amount||0),0);
  const cash=paid-spent;
  const expected=total-spent;
  const pct=total?Math.min(100,paid/total*100):0;
  return`<div class=ref-month><button class=ghost onclick="moveReportMonth(-1)">‹</button><b>${month}</b><button class=ghost onclick="moveReportMonth(1)">›</button></div>
  <div class=grid>
    ${metric('Total Receivable','AED '+money(total))}
    ${metric('Collected','AED '+money(paid))}
    ${metric('Pending to Collect','AED '+money(due))}
    ${metric('Expenses','AED '+money(spent))}
    ${metric('Current Cash Balance','AED '+money(cash))}
    ${metric('Expected Month Balance','AED '+money(expected))}
  </div>
  <div class=card style="margin-top:12px"><div class=top><div><h3 style="margin:0">Collection Progress</h3><div class=small>AED ${money(paid)} collected of AED ${money(total)}</div></div><b>${pct.toFixed(1)}%</b></div><div class=ref-progress><i style="width:${pct}%"></i></div></div>
  <div class=ref-actions><button class="card ref-action" onclick="exportMemberReport()"><b>👥 Member Report</b><small class=muted>Payment status and dues</small></button><button class="card ref-action" onclick="exportExpenseReport()"><b>🧾 Expense Report</b><small class=muted>Detailed expense breakdown</small></button><button class="card ref-action" onclick="exportFullReport()"><b>📥 Export Report</b><small class=muted>Complete CSV download</small></button></div>`
}'''

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    a=s.find('function reports(){')
    b=s.find('\nfunction settings(){',a)
    if a<0 or b<0:
        raise SystemExit('Reports function markers missing')
    s=s[:a]+REPORTS+s[b:]
    required=['Total Receivable','Pending to Collect','Current Cash Balance','Expected Month Balance','Collection Progress','pct.toFixed(1)']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Report UI patch missing: '+', '.join(missing))
    if 'How this report is calculated' in s:
        raise SystemExit('Formula explanation must not be visible in report UI')
    app.write_text(s)
    print('Applied clean monthly report UI to',app)
