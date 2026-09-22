from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

HELPERS=r'''
function pendingPaymentMembers(month){
  return state.data.members.map(m=>({m,q:memberSummary(m,month)})).filter(x=>Number(x.q.due||0)>.009)
}
function pendingPaymentMessage(name,month,plan,paid,due){
  return `A2 MESS HUB
Hi ${name},

Our current mess cash balance is low, and the available amount may be used for essential purchases within the next 1–2 days.

Your ${month} mess payment is still pending.
Total: AED ${money(plan)}
Paid: AED ${money(paid)}
Balance due: AED ${money(due)}

Please complete the pending payment as soon as possible so we can continue purchasing mess supplies without interruption.

Thank you.
— A2 MESS HUB`
}
window.sendPendingPaymentWhatsApp=(memberId,month)=>{
  const m=state.data.members.find(x=>String(x.id)===String(memberId));
  if(!m)return toast('Member not found');
  const q=memberSummary(m,month),phone=String(m.phone||'').replace(/\D/g,'');
  if(!phone)return toast((m.name||'Member')+' has no WhatsApp number');
  const text=encodeURIComponent(pendingPaymentMessage(m.name||'Member',month,q.plan,q.paid,q.due));
  window.open(`https://wa.me/${phone}?text=${text}`,'_blank','noopener')
};
window.openPendingPaymentReminders=()=>{
  if(state.profile?.role!=='admin')return toast('Admin only');
  const month=window._reportMonth||currentBillingMonth(),rows=pendingPaymentMembers(month);
  if(!rows.length)return toast('All members are fully paid for '+month);
  const total=rows.reduce((a,x)=>a+Number(x.q.due||0),0);
  modal(`<div class=top><div><h3 style="margin:0">💬 Notify Pending Members</h3><div class=small>${rows.length} unpaid member(s) · AED ${money(total)} pending</div></div><button class=ghost onclick=closeM()>✕</button></div><div class=note style="margin-top:12px">The same cash-low reminder is prepared separately for every Due or Partial member. Tap WhatsApp, then tap Send. Fully paid members are excluded.</div><div class=list style="margin-top:12px">${rows.map(({m,q})=>`<div class=row><span><b>${esc(m.name||'Member')}</b><small class=muted> · ${q.status} · Due AED ${money(q.due)}</small></span><span>${m.phone?esc(m.phone):'<span class=muted>No phone</span>'}</span><span></span><span><button class=btn ${m.phone?'':'disabled'} onclick="sendPendingPaymentWhatsApp('${esc(m.id)}','${month}')">WhatsApp</button></span></div>`).join('')}</div><div class=note style="margin-top:12px">WhatsApp does not permit silent bulk sending from this free web app. Each message opens ready to send, protecting members’ phone numbers and avoiding an exposed group chat.</div>`)
};
'''

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    report_marker='<div class=ref-actions><button class="card ref-action" onclick="exportMemberReport()"'
    alert='''${cash<200&&due>0?`<div class="card v6-alert danger" style="margin-top:12px"><div class=top><div><b>⚠️ Current cash balance is low</b><div class=small>AED ${money(cash)} available · AED ${money(due)} still pending</div></div><button class=btn onclick="openPendingPaymentReminders()">WhatsApp Pending Members</button></div><div class=small style="margin-top:10px">Cash is below AED 200. Send the common payment reminder to all Due and Partial members.</div></div>`:''}
  '''
    if 'openPendingPaymentReminders()' not in s:
        if report_marker not in s:
            raise SystemExit('Final report action marker missing')
        s=s.replace(report_marker,alert+report_marker,1)
        marker='function render(){'
        if marker not in s:
            raise SystemExit('Render marker missing')
        s=s.replace(marker,HELPERS+'\n'+marker,1)
    required=['pendingPaymentMembers(','pendingPaymentMessage(','openPendingPaymentReminders','WhatsApp Pending Members','cash<200&&due>0','Due or Partial']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Pending WhatsApp reminder missing: '+', '.join(missing))
    app.write_text(s)
    print('Added low-cash WhatsApp reminders for pending members to',app)
