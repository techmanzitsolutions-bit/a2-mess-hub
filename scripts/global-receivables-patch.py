from pathlib import Path

app = Path('/tmp/a2-pwa/www/app.html')
if not app.exists():
    app = Path('www/app.html')
s = app.read_text()

helper = r'''function memberSnapshotPaid(m,month=currentBillingMonth()){
  const txPaid=memberPaid(m,month);
  if(state.profile?.role==='admin') return txPaid;
  const snapMonth=String(m?.currentBillingMonth||'');
  const snap=Number(m?.paidAmount||0);
  if(snapMonth===month || !snapMonth) return Number.isFinite(snap)?Math.max(0,snap):0;
  return 0;
}
function globalPaymentSummary(month=currentBillingMonth()){
  let receivable=0,received=0;
  state.data.members.forEach(m=>{
    const plan=planValue(m?.planAmount||m?.plan);
    const paid=Math.min(plan,memberSnapshotPaid(m,month));
    receivable+=plan;
    received+=paid;
  });
  return {receivable,received,balance:Math.max(0,receivable-received),month};
}
'''

if 'function globalPaymentSummary(' not in s:
    marker='function dashboard(){'
    if marker not in s:
        raise SystemExit('dashboard marker not found')
    s=s.replace(marker,helper+'\n'+marker,1)

start=s.find('function dashboard(){')
end=s.find('function users(){',start)
if start<0 or end<0:
    raise SystemExit('dashboard block markers not found')

dashboard = r'''function dashboard(){
  const month=currentBillingMonth(),g=globalPaymentSummary(month);
  if(state.profile.role==='member'){
    const member=linkedMember(auth.currentUser.uid);
    if(!member)return`<div class=card style="margin-top:14px"><h3>Member account not linked</h3><p class=muted>Ask Admin to link this login to your member record.</p></div>`;
    const q=memberSummary(member,month),expenses=currentMonthExpenses(),totalExpense=expenses.reduce((a,x)=>a+Number(x.amount||0),0),cats={};
    expenses.forEach(x=>{const k=x.category||'General';cats[k]=(cats[k]||0)+Number(x.amount||0)});
    const entries=Object.entries(cats).sort((a,b)=>b[1]-a[1]),max=Math.max(1,...entries.map(x=>x[1])),progress=q.plan?Math.min(100,(q.paid/q.plan)*100):0;
    return`<div class=note style="margin-top:12px">Billing month: <b>${month}</b> · Your status: <b>${q.status}</b></div><div class=grid>${metric('Total Receivable (All Members)','AED '+money(g.receivable))}${metric('Total Received (All Members)','AED '+money(g.received))}${metric('Balance Pending (All Members)','AED '+money(g.balance))}${metric('You Paid','AED '+money(q.paid))}${metric('Your Balance Due','AED '+money(q.due))}${metric('Total Mess Expense','AED '+money(totalExpense))}</div><div class=card style="margin-top:12px"><div class=top><div><h3 style="margin:0">Your Payment Progress</h3><div class=small>Read only</div></div><b>${progress.toFixed(0)}%</b></div><div style="height:12px;background:#ffffff10;border-radius:99px;overflow:hidden;margin-top:12px"><div style="height:100%;width:${progress}%;background:linear-gradient(90deg,#45f0a6,#f6cb67);border-radius:99px"></div></div></div><div class=card style="margin-top:12px"><div class=top><div><h3 style="margin:0">Expense Chart</h3><div class=small>${month} · view only</div></div><b>AED ${money(totalExpense)}</b></div><div class=list style="margin-top:14px">${entries.length?entries.map(([name,val])=>`<div><div class=top style="font-size:13px"><span>${esc(name)}</span><b>AED ${money(val)}</b></div><div style="height:10px;background:#ffffff10;border-radius:99px;overflow:hidden;margin-top:6px"><div style="height:100%;width:${Math.max(4,(val/max)*100)}%;background:linear-gradient(90deg,#45f0a6,#f6cb67);border-radius:99px"></div></div></div>`).join(''):'<p class=muted>No expenses recorded this month.</p>'}</div></div>`
  }
  const summaries=state.data.members.map(m=>memberSummary(m,month)),exp=currentMonthExpenses().reduce((a,x)=>a+Number(x.amount||0),0),paidCount=summaries.filter(q=>q.status==='PAID').length,partialCount=summaries.filter(q=>q.status==='PARTIAL').length,dueCount=summaries.filter(q=>q.status==='DUE').length;
  return`<div class=note style="margin-top:12px">Billing month: <b>${month}</b> · Paid ${paidCount} · Partial ${partialCount} · Due ${dueCount}</div><div class=grid>${metric('Total Receivable','AED '+money(g.receivable))}${metric('Total Received','AED '+money(g.received))}${metric('Balance Pending','AED '+money(g.balance))}${metric('Members',state.data.members.length)}${metric('Expenses','AED '+money(exp))}</div>`
}
'''

s=s[:start]+dashboard+'\n'+s[end:]

required=['function globalPaymentSummary(','Total Receivable (All Members)','Total Received (All Members)','Balance Pending (All Members)',"metric('Total Receivable'","metric('Total Received'","metric('Balance Pending'"]
missing=[x for x in required if x not in s]
if missing:
    raise SystemExit('Global receivables patch missing: '+', '.join(missing))

app.write_text(s)
print('Added global receivable, received and balance totals for member/admin dashboards')
