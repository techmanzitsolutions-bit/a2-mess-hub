from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    # Add monthly closings to realtime admin state.
    s=s.replace("users:[]}","users:[],monthlyClosings:[]}")
    old="if(state.profile.role==='admin')state.unsubs.push(onSnapshot(collection(db,'users'),s=>{state.data.users=s.docs.map(d=>({id:d.id,...d.data()}));render()}))"
    new="if(state.profile.role==='admin'){state.unsubs.push(onSnapshot(collection(db,'users'),s=>{state.data.users=s.docs.map(d=>({id:d.id,...d.data()}));render()}));state.unsubs.push(onSnapshot(collection(db,'monthlyClosings'),s=>{state.data.monthlyClosings=s.docs.map(d=>({id:d.id,...d.data()}));render()}))}"
    if old in s:
        s=s.replace(old,new,1)

    # Admin navigation + labels.
    s=s.replace("['dashboard','users','members','meals','inventory','expenses','payments','gas','reports','backup','settings']","['dashboard','users','members','meals','inventory','expenses','payments','gas','closing','reports','backup','settings']")
    s=s.replace("['dashboard','users','members','meals','inventory','expenses','payments','reports','backup','settings']","['dashboard','users','members','meals','inventory','expenses','payments','closing','reports','backup','settings']")
    if "closing:'Month Close'" not in s:
        s=s.replace("reports:'Reports',backup:'Backup',settings:'Settings'","closing:'Month Close',reports:'Reports',backup:'Backup',settings:'Settings'")
        s=s.replace("gas:'Order Gas',reports:'Reports',backup:'Backup',settings:'Settings'","gas:'Order Gas',closing:'Month Close',reports:'Reports',backup:'Backup',settings:'Settings'")

    if 'function monthClosePage(){' not in s:
        marker='function reports(){'
        if marker not in s:
            raise SystemExit('reports marker not found')
        code=r'''function previousMonthKey(month){const [y,m]=String(month).split('-').map(Number),d=new Date(y,m-2,1);return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`}
function closingDoc(month){return(state.data.monthlyClosings||[]).find(x=>String(x.id||x.month)===String(month))||null}
function priorClosingBalance(m,month){const prev=closingDoc(previousMonthKey(month));if(prev&&Array.isArray(prev.members)){const r=prev.members.find(x=>String(x.memberId||'')===String(m.id||'')||String(x.uid||'')===String(m.uid||''));if(r)return Number(r.closingBalance||0)}if(String(m.carryToMonth||'')===String(month))return Number(m.carryBalance||0);return 0}
function closingPreview(month){const members=state.data.members.filter(m=>m.active!==false&&planValue(m.planAmount||m.plan)>0),expenses=state.data.expenses.filter(x=>recordMonth(x)===month),totalExpense=expenses.reduce((a,x)=>a+Number(x.amount||0),0),weights=members.map(m=>({m,weight:planValue(m.planAmount||m.plan)/200})),totalWeight=weights.reduce((a,x)=>a+x.weight,0),unit=totalWeight?totalExpense/totalWeight:0;const rows=weights.map(({m,weight})=>{const opening=priorClosingBalance(m,month),paid=memberPaid(m,month),share=unit*weight,available=opening+paid,closingBalance=available-share;return{memberId:m.id,uid:m.uid||'',name:m.name||'Member',plan:planValue(m.planAmount||m.plan),weight,openingBalance:opening,paid,expenseShare:share,available,closingBalance,status:closingBalance>0.005?'ADVANCE':closingBalance<-0.005?'DUE':'SETTLED',carryForward:Math.abs(closingBalance)}});return{month,totalExpense,totalWeight,unit,totalPaid:rows.reduce((a,x)=>a+x.paid,0),totalOpening:rows.reduce((a,x)=>a+x.openingBalance,0),totalDue:rows.reduce((a,x)=>a+Math.max(0,-x.closingBalance),0),totalAdvance:rows.reduce((a,x)=>a+Math.max(0,x.closingBalance),0),expenseCount:expenses.length,paymentCount:state.data.payments.filter(x=>paymentMonth(x)===month).length,members:rows}}
function monthClosePage(){if(state.profile.role!=='admin')return`<div class=note style="margin-top:14px">Admin only.</div>`;const month=currentBillingMonth(),saved=closingDoc(month);return`<div class=card style="margin-top:14px"><div class=top><div><h3 style="margin:0">📒 Monthly Closing</h3><div class=small>Final expense settlement + due/advance carry forward</div></div><span class=tag>${saved?'SAVED':'PREVIEW'}</span></div><div class=form style="margin-top:14px"><div class=field><label>Closing Month</label><input id=closeMonth type=month value="${month}" onchange=renderClosingPreview()></div><div class=field><label>Calculation</label><input value="AED 200 = 1.00 share · 100 = 0.50 · 250 = 1.25" readonly></div><div class=span2><div class=note>All monthly expenses are distributed by plan weight. Member opening advance/due + payments are compared with that member's expense share. Positive balance becomes next-month advance; negative balance becomes due.</div></div></div><div id=closingPreview style="margin-top:12px"></div></div><div class=card style="margin-top:14px"><h3 style="margin-top:0">Stored Closing Reports</h3><div class=list>${(state.data.monthlyClosings||[]).sort((a,b)=>String(b.month||b.id).localeCompare(String(a.month||a.id))).map(r=>`<div class=row><span><b>${esc(r.month||r.id)}</b><small class=muted> · ${Number(r.memberCount||r.members?.length||0)} members</small></span><span>Expense AED ${money(r.totalExpense)}</span><span>${r.status||'CLOSED'}</span><span><button class=ghost onclick="downloadClosingReport('${esc(r.month||r.id)}')">Download</button></span></div>`).join('')||'<p class=muted>No monthly closing reports saved yet.</p>'}</div></div>`}
window.renderClosingPreview=()=>{const box=$('closingPreview');if(!box)return;const month=$('closeMonth')?.value||currentBillingMonth(),q=closingPreview(month),saved=closingDoc(month);box.innerHTML=`<div class=grid>${metric('Total Expense','AED '+money(q.totalExpense))}${metric('Payments','AED '+money(q.totalPaid))}${metric('Due Carry','AED '+money(q.totalDue))}${metric('Advance Carry','AED '+money(q.totalAdvance))}</div><div class=card style="margin-top:12px"><div class=top><h3 style="margin:0">Member Settlement</h3><div class=small>${q.members.length} active members · weighted units ${money(q.totalWeight)}</div></div><div class=list style="margin-top:12px">${q.members.map(r=>`<div class=row><span><b>${esc(r.name)}</b><small class=muted> · Plan ${money(r.plan)} · Weight ${r.weight.toFixed(2)}</small></span><span>Share AED ${money(r.expenseShare)}<br><small class=muted>Opening ${r.openingBalance>=0?'+':''}${money(r.openingBalance)} · Paid ${money(r.paid)}</small></span><span class="tag ${r.status==='DUE'?'due':r.status==='ADVANCE'?'paid':''}">${r.status}<br>${r.status!=='SETTLED'?'AED '+money(r.carryForward):''}</span><span></span></div>`).join('')||'<p class=muted>No active members with plans.</p>'}</div></div><div class=actions style="margin-top:12px"><button class=btn onclick=closeSelectedMonth()>${saved?'RECALCULATE & UPDATE':'CLOSE MONTH & SAVE REPORT'}</button>${saved?`<button class=ghost onclick="downloadClosingReport('${month}')">DOWNLOAD REPORT</button>`:''}</div>`}
window.closeSelectedMonth=async()=>{if(state.profile?.role!=='admin')return toast('Admin only');const month=$('closeMonth')?.value||currentBillingMonth(),q=closingPreview(month);if(!q.members.length)return toast('No active members to close');if(!ask(`Close ${month}?\n\nExpense: AED ${money(q.totalExpense)}\nMembers: ${q.members.length}\nDue carry: AED ${money(q.totalDue)}\nAdvance carry: AED ${money(q.totalAdvance)}\n\nThis stores a permanent monthly closing snapshot and updates carry balances for the next month.`))return;try{const next=(()=>{const[y,m]=month.split('-').map(Number),d=new Date(y,m,1);return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`})(),report={month,status:'CLOSED',memberCount:q.members.length,totalExpense:q.totalExpense,totalPaid:q.totalPaid,totalOpening:q.totalOpening,totalDue:q.totalDue,totalAdvance:q.totalAdvance,totalWeight:q.totalWeight,unitExpense:q.unit,expenseCount:q.expenseCount,paymentCount:q.paymentCount,members:q.members,closedBy:auth.currentUser.uid,closedByEmail:state.profile.email||'',closedAt:serverTimestamp(),updatedAt:serverTimestamp()};let b=writeBatch(db);b.set(doc(db,'monthlyClosings',month),report,{merge:true});for(const r of q.members){if(!r.memberId)continue;b.update(doc(db,'members',r.memberId),{carryBalance:r.closingBalance,carryFromMonth:month,carryToMonth:next,lastClosedMonth:month,lastExpenseShare:r.expenseShare,advanceAmount:Math.max(0,r.closingBalance),dueAmount:Math.max(0,-r.closingBalance),updatedAt:serverTimestamp()})}await b.commit();toast(`${month} closed and report stored`)}catch(e){err(e)}}
window.downloadClosingReport=month=>{const r=closingDoc(month);if(!r)return toast('Closing report not found');const head=['Member','Plan','Weight','Opening Balance','Paid','Expense Share','Closing Balance','Status'],lines=[head.join(',')];(r.members||[]).forEach(x=>lines.push([x.name,x.plan,x.weight,x.openingBalance,x.paid,x.expenseShare,x.closingBalance,x.status].map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')));lines.push('');lines.push(`"Total Expense","${r.totalExpense||0}"`);lines.push(`"Total Paid","${r.totalPaid||0}"`);lines.push(`"Total Due","${r.totalDue||0}"`);lines.push(`"Total Advance","${r.totalAdvance||0}"`);const blob=new Blob([lines.join('\n')],{type:'text/csv'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`A2-MESS-HUB-CLOSING-${month}.csv`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500)}
'''
        s=s.replace(marker,code+marker,1)

    # Renderer map.
    s=s.replace('{dashboard,users,members,meals,inventory,expenses,payments,gas:gasOrder,reports,backup:backupPage,settings}','{dashboard,users,members,meals,inventory,expenses,payments,gas:gasOrder,closing:monthClosePage,reports,backup:backupPage,settings}')
    s=s.replace('{dashboard,users,members,meals,inventory,expenses,payments,reports,backup:backupPage,settings}','{dashboard,users,members,meals,inventory,expenses,payments,closing:monthClosePage,reports,backup:backupPage,settings}')

    # Make monthly backup include the selected closing report and restore it.
    s=s.replace("data:{members:state.data.members.map(backupPlain),inventory:state.data.inventory.map(backupPlain),meals:state.data.meals.map(backupPlain),payments:state.data.payments.filter(x=>backupMonthOf(x)===month).map(backupPlain),expenses:state.data.expenses.filter(x=>backupMonthOf(x)===month).map(backupPlain)}","data:{members:state.data.members.map(backupPlain),inventory:state.data.inventory.map(backupPlain),meals:state.data.meals.map(backupPlain),payments:state.data.payments.filter(x=>backupMonthOf(x)===month).map(backupPlain),expenses:state.data.expenses.filter(x=>backupMonthOf(x)===month).map(backupPlain),monthlyClosings:(state.data.monthlyClosings||[]).filter(x=>String(x.id||x.month)===month).map(backupPlain)}")
    s=s.replace("const cols=['members','inventory','meals','payments','expenses']","const cols=['members','inventory','meals','payments','expenses','monthlyClosings']")

    # Render preview after page navigation/render.
    old="function render(){if(!state.profile)return;const pages="
    if old in s and 'setTimeout(renderClosingPreview,0)' not in s:
        # handled below with targeted renderer replacement when available
        pass
    # Most builds finish renderer with layout(pages[state.page]?.()||dashboard())
    needle="layout(pages[state.page]?.()||dashboard())}"
    if needle in s:
        s=s.replace(needle,"layout(pages[state.page]?.()||dashboard());if(state.page==='closing')setTimeout(renderClosingPreview,0)}",1)

    required=['function monthClosePage(){','function closingPreview(month){','window.closeSelectedMonth=async','monthlyClosings','carryToMonth','ADVANCE','DUE',"closing:'Month Close'",'closing:monthClosePage','A2-MESS-HUB-CLOSING-']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Monthly closing patch missing: '+', '.join(missing))
    app.write_text(s)
    print(f'Added weighted monthly closing and carry-forward reports to {app}')
