from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

decode=lambda x:x.replace('§',chr(96)).replace('¤',chr(36))

SUMMARY=decode(r'''function memberSummary(m,month=currentBillingMonth()){const plan=planValue(m?.planAmount||m?.plan),paid=memberPaid(m,month),opening=priorClosingBalance(m,month),available=opening+paid,due=Math.max(0,plan-available),advance=Math.max(0,available-plan),status=advance>0.005?'ADVANCE':due<=0.005?'PAID':available>0.005?'PARTIAL':'DUE';return{plan,paid,opening,carryForward:opening,available,due,advance,status,month}}''')

WA=decode(r'''window.waDue=(phone,name,month,plan,paid,opening,due,advance)=>{const carryLine=Number(opening)>=0?'Advance carry forward: AED '+money(Math.abs(opening)):'Due carry forward: AED '+money(Math.abs(opening)),text=encodeURIComponent(§A2 MESS HUB
Hi ¤{name}, payment update for ¤{month}:
Plan: AED ¤{money(plan)}
¤{carryLine}
Paid this month: AED ¤{money(paid)}
Balance due: AED ¤{money(due)}
Advance balance: AED ¤{money(advance)}
Status: ¤{Number(advance)>0?'ADVANCE':Number(due)<=0?'PAID':'PENDING'}
— Powered by TM SOLUTIONS§);window.open(§https://wa.me/¤{String(phone||'').replace(/\D/g,'')}?text=¤{text}§,'_blank','noopener')};''')

PENDING=decode(r'''function pendingPaymentMessage(name,month,plan,paid,due,opening=0,advance=0){
  const carryLine=Number(opening)>=0?§Advance carry forward: AED ¤{money(Math.abs(opening))}§:§Due carry forward: AED ¤{money(Math.abs(opening))}§;
  return §A2 MESS HUB
Hi ¤{name},

Our current mess cash balance is low, and the available amount may be used for essential purchases within the next 1–2 days.

Your ¤{month} mess payment status:
Plan: AED ¤{money(plan)}
¤{carryLine}
Paid this month: AED ¤{money(paid)}
Balance due: AED ¤{money(due)}
Advance balance: AED ¤{money(advance)}

¤{Number(due)>0?'Please complete the pending payment as soon as possible so we can continue purchasing mess supplies without interruption.':'Your account has no pending payment.'}

Thank you.
— A2 MESS HUB§
}''')

def replace_between(s,start,end,replacement):
    a=s.find(start); b=s.find(end,a)
    if a<0 or b<0: raise SystemExit(f'Markers missing: {start} / {end}')
    return s[:a]+replacement+s[b:]

for app in paths:
    if not app.exists(): raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    s=replace_between(s,'function memberSummary(', '\nfunction currentMonthExpenses(',SUMMARY)
    s=replace_between(s,'window.waDue=', '\nwindow.delRecord=',WA)
    s=replace_between(s,'function pendingPaymentMessage(', '\nwindow.sendPendingPaymentWhatsApp=',PENDING)
    s=s.replace(decode("pendingPaymentMessage(m.name||'Member',month,q.plan,q.paid,q.due)"),decode("pendingPaymentMessage(m.name||'Member',month,q.plan,q.paid,q.due,q.opening,q.advance)"))
    s=s.replace(decode("waDue('¤{esc(m.phone||'')}','¤{esc(m.name||'Member')}',¤{q.plan},¤{q.paid},¤{q.due})"),decode("waDue('¤{esc(m.phone||'')}','¤{esc(m.name||'Member')}','¤{month}',¤{q.plan},¤{q.paid},¤{q.opening},¤{q.due},¤{q.advance})"))
    s=s.replace(decode("Paid AED ¤{money(q.paid)}<br><small class=muted>Due AED ¤{money(q.due)}</small>"),decode("Paid AED ¤{money(q.paid)}<br><small class=muted>Carry Forward ¤{q.opening>=0?'+':'−'} AED ¤{money(Math.abs(q.opening))}</small><br><small class=muted>¤{q.advance>0?'Advance AED '+money(q.advance):'Due AED '+money(q.due)}</small>"))
    s=s.replace(decode("¤{metric('Paid','AED '+money(q.paid))}¤{metric('Due','AED '+money(q.due))}"),decode("¤{metric('Paid This Month','AED '+money(q.paid))}¤{metric('Carry Forward',(q.opening>=0?'+ ':'− ')+'AED '+money(Math.abs(q.opening)))}¤{metric(q.advance>0?'Advance':'Due','AED '+money(q.advance>0?q.advance:q.due))}"))
    s=s.replace("if(total>plan+0.001)return toast('Payment exceeds remaining due');const due=Math.max(0,plan-total),status=paymentStatus(plan,total),v=", "const opening=priorClosingBalance(m,billingMonth),available=opening+total,due=Math.max(0,plan-available),advance=Math.max(0,available-plan),status=advance>0.005?'ADVANCE':due<=0.005?'PAID':available>0.005?'PARTIAL':'DUE',v=")
    s=s.replace("dueAmount:due,status,updatedAt:", "openingCarry:opening,availableAmount:available,dueAmount:due,advanceAmount:advance,status,updatedAt:")
    s=s.replace("paidAmount:total,dueAmount:due,status,currentBillingMonth:", "paidAmount:total,dueAmount:due,advanceAmount:advance,status,currentBillingMonth:")
    s=s.replace("toast('Payment saved · Paid AED '+money(total)+' · Due AED '+money(due)+' · '+status)", "toast('Payment saved · Carry '+(opening>=0?'+':'−')+' AED '+money(Math.abs(opening))+' · Due AED '+money(due)+' · Advance AED '+money(advance))")
    s=s.replace("total=other+entry,due=Math.max(0,plan-total),status=paymentStatus(plan,total);", "total=other+entry,opening=m?priorClosingBalance(m,month):0,available=opening+total,due=Math.max(0,plan-available),advance=Math.max(0,available-plan),status=advance>0.005?'ADVANCE':due<=0.005?'PAID':available>0.005?'PARTIAL':'DUE';")
    s=s.replace("if(¤('pdue'))¤('pdue').value='AED '+money(due);if(¤('pstatus'))".replace('¤',chr(36)), "if(¤('pdue'))¤('pdue').value='AED '+money(due)+(advance>0?' · Advance AED '+money(advance):'');if(¤('pstatus'))".replace('¤',chr(36)))
    old_export=decode("window.exportMemberReport=()=>{const m=window._reportMonth||currentBillingMonth();downloadCsv(§A2-Members-¤{m}.csv§,[['Member','Plan AED','Paid AED','Due AED','Status'],...state.data.members.map(x=>{const q=memberSummary(x,m);return[x.name,q.plan,q.paid,q.due,q.status]})])}")
    new_export=decode("window.exportMemberReport=()=>{const m=window._reportMonth||currentBillingMonth();downloadCsv(§A2-Members-¤{m}.csv§,[['Member','Plan AED','Carry Forward AED','Paid This Month AED','Due AED','Advance AED','Status'],...state.data.members.map(x=>{const q=memberSummary(x,m);return[x.name,q.plan,q.opening,q.paid,q.due,q.advance,q.status]})])}")
    if old_export not in s: raise SystemExit('Member export marker missing')
    s=s.replace(old_export,new_export,1)
    required=['carryForward:opening','Advance carry forward: AED','Due carry forward: AED','q.opening,q.advance','Carry Forward AED','advanceAmount:advance','Payment saved · Carry']
    missing=[x for x in required if x not in s]
    if missing: raise SystemExit('Carry-forward features missing: '+', '.join(missing))
    app.write_text(s)
    print('Added month-wise carry forward to balances, payments and WhatsApp:',app)
