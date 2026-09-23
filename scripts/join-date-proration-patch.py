from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

HELPERS=r'''
function monthDayRange(month){
  const [year,mon]=String(month).split('-').map(Number),days=new Date(year,mon,0).getDate();
  return{days,start:`${month}-01`,end:`${month}-${String(days).padStart(2,'0')}`}
}
function memberActiveDays(m,month){
  const range=monthDayRange(month),joined=String(m?.joinDate||'').slice(0,10);
  if(!joined||joined<=range.start)return range.days;
  if(joined>range.end)return 0;
  const joinDay=Number(joined.slice(8,10));
  return Math.max(0,range.days-joinDay+1)
}
function memberEffectiveWeight(m,month){
  const range=monthDayRange(month),days=memberActiveDays(m,month),base=planValue(m.planAmount||m.plan)/200;
  return base*(days/range.days)
}
'''

MEMBER_FORM=r'''window.memberForm=(x={})=>{const q=x.id?memberSummary(x):{plan:planValue(x.plan||'AED 200'),paid:0,due:planValue(x.plan||'AED 200'),status:'DUE'},joinDate=String(x.joinDate||(!x.id?new Date().toISOString().slice(0,10):'')).slice(0,10);modal(`<div class=top><h3>${x.id?'Edit':'Add'} Member</h3><button class=ghost onclick=closeM()>✕</button></div><div class=form><div class=field><label>Name</label><input id=mname value="${esc(x.name||'')}"></div><div class=field><label>Monthly Plan</label><select id=mplan><option ${q.plan===100?'selected':''}>AED 100</option><option ${q.plan===200?'selected':''}>AED 200</option><option ${q.plan===250?'selected':''}>AED 250</option></select></div><div class=field><label>Join Date</label><input id=mjoin type=date value="${esc(joinDate)}"></div><div class=field><label>First Month Calculation</label><input value="Actual active days only" readonly></div><div class=field><label>${currentBillingMonth()} Status</label><input value="${q.status}" readonly></div><div class=field><label>Paid / Due</label><input value="AED ${money(q.paid)} paid · AED ${money(q.due)} due" readonly></div><div class=field><label>Phone</label><input id=mphone value="${esc(x.phone||'')}"></div><div class="span2 note">Join day is included. At month-end, this member receives only the expense share for active days. Any extra payment becomes next-month advance; any shortage becomes due.</div><div class=span2><button class=btn onclick="saveMember('${x.id||''}')">SAVE</button></div></div>`)};'''

MEMBER_BY_ID=r'''window.memberFormById=id=>memberForm(state.data.members.find(x=>x.id===id)||{});'''

SAVE_MEMBER=r'''window.saveMember=async id=>{try{const old=state.data.members.find(x=>x.id===id)||{},plan=$('mplan').value,planAmount=planValue(plan),probe={...old,id:id||old.id,plan,planAmount},q=id?memberSummary(probe):{paid:0,due:planAmount,status:'DUE'},joinDate=$('mjoin').value,v={name:$('mname').value.trim(),plan,planAmount,joinDate,paidAmount:q.paid,dueAmount:Math.max(0,planAmount-q.paid),status:paymentStatus(planAmount,q.paid),currentBillingMonth:currentBillingMonth(),phone:$('mphone').value.trim(),updatedAt:serverTimestamp()};if(!v.name)return toast('Enter member name');if(!joinDate&&!id)return toast('Select join date');id?await updateDoc(doc(db,'members',id),v):await addDoc(collection(db,'members'),{...v,createdAt:serverTimestamp()});closeM();toast('Member saved'+(joinDate?' · join date '+joinDate:''))}catch(e){err(e)}};'''

CLOSING=r'''function closingPreview(month){const range=monthDayRange(month),members=state.data.members.filter(m=>m.active!==false&&planValue(m.planAmount||m.plan)>0&&memberActiveDays(m,month)>0),expenses=state.data.expenses.filter(x=>recordMonth(x)===month),totalExpense=expenses.reduce((a,x)=>a+Number(x.amount||0),0),weights=members.map(m=>{const activeDays=memberActiveDays(m,month),baseWeight=planValue(m.planAmount||m.plan)/200,effectiveWeight=memberEffectiveWeight(m,month);return{m,activeDays,baseWeight,effectiveWeight}}),totalWeight=weights.reduce((a,x)=>a+x.effectiveWeight,0),unit=totalWeight?totalExpense/totalWeight:0;const rows=weights.map(({m,activeDays,baseWeight,effectiveWeight})=>{const opening=priorClosingBalance(m,month),paid=memberPaid(m,month),share=unit*effectiveWeight,available=opening+paid,closingBalance=available-share;return{memberId:m.id,uid:m.uid||'',name:m.name||'Member',joinDate:m.joinDate||'',daysInMonth:range.days,activeDays,plan:planValue(m.planAmount||m.plan),baseWeight,weight:effectiveWeight,effectiveWeight,openingBalance:opening,paid,expenseShare:share,available,closingBalance,status:closingBalance>0.005?'ADVANCE':closingBalance<-0.005?'DUE':'SETTLED',carryForward:Math.abs(closingBalance)}});return{month,daysInMonth:range.days,totalExpense,totalWeight,unit,totalPaid:rows.reduce((a,x)=>a+x.paid,0),totalOpening:rows.reduce((a,x)=>a+x.openingBalance,0),totalDue:rows.reduce((a,x)=>a+Math.max(0,-x.closingBalance),0),totalAdvance:rows.reduce((a,x)=>a+Math.max(0,x.closingBalance),0),expenseCount:expenses.length,paymentCount:state.data.payments.filter(x=>paymentMonth(x)===month).length,members:rows}}'''

RENDER=r'''window.renderClosingPreview=()=>{const box=$('closingPreview');if(!box)return;const month=$('closeMonth')?.value||currentBillingMonth(),q=closingPreview(month),saved=closingDoc(month);box.innerHTML=`<div class=grid>${metric('Total Expense','AED '+money(q.totalExpense))}${metric('Payments','AED '+money(q.totalPaid))}${metric('Due Carry','AED '+money(q.totalDue))}${metric('Advance Carry','AED '+money(q.totalAdvance))}</div><div class=card style="margin-top:12px"><div class=top><h3 style="margin:0">Member Settlement</h3><div class=small>${q.members.length} active members · effective units ${money(q.totalWeight)}</div></div><div class=list style="margin-top:12px">${q.members.map(r=>`<div class=row><span><b>${esc(r.name)}</b><small class=muted> · Plan ${money(r.plan)} · ${r.activeDays}/${r.daysInMonth} active days</small>${r.joinDate?`<small class=muted> · Joined ${esc(r.joinDate)}</small>`:''}</span><span>Share AED ${money(r.expenseShare)}<br><small class=muted>Effective weight ${r.effectiveWeight.toFixed(3)} · Paid ${money(r.paid)}</small></span><span class="tag ${r.status==='DUE'?'due':r.status==='ADVANCE'?'paid':''}">${r.status}<br>${r.status!=='SETTLED'?'AED '+money(r.carryForward):''}</span><span></span></div>`).join('')||'<p class=muted>No active members with plans.</p>'}</div></div><div class=actions style="margin-top:12px"><button class=btn onclick=closeSelectedMonth()>${saved?'RECALCULATE & UPDATE':'CLOSE MONTH & SAVE REPORT'}</button>${saved?`<button class=ghost onclick="downloadClosingReport('${month}')">DOWNLOAD REPORT</button>`:''}</div>`}'''

def replace_between(s,start,end,replacement):
    a=s.find(start)
    b=s.find(end,a)
    if a<0 or b<0:
        raise SystemExit(f'Markers missing: {start} / {end}')
    return s[:a]+replacement+s[b:]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    if 'function memberActiveDays(' not in s:
        marker='function priorClosingBalance('
        if marker not in s:
            raise SystemExit('Closing helper marker missing')
        s=s.replace(marker,HELPERS+'\n'+marker,1)
    s=replace_between(s,'window.memberForm=', '\nwindow.memberFormById=', MEMBER_FORM)
    s=replace_between(s,'window.memberFormById=', '\nwindow.saveMember=', MEMBER_BY_ID)
    s=replace_between(s,'window.saveMember=', '\nfunction meals(){', SAVE_MEMBER)
    s=replace_between(s,'function closingPreview(month){','\nfunction monthClosePage(){',CLOSING)
    s=replace_between(s,'window.renderClosingPreview=', '\nwindow.closeSelectedMonth=',RENDER)
    s=s.replace('AED 200 = 1.00 share · 100 = 0.50 · 250 = 1.25','Plan weight × active days in closing month')
    s=s.replace('All monthly expenses are distributed by plan weight. Member opening advance/due + payments are compared with that member\'s expense share. Positive balance becomes next-month advance; negative balance becomes due.','Monthly expenses are distributed by plan weight and active days. A new joiner is charged only from the join date through month-end. Extra payment becomes next-month advance; shortage becomes due.')
    required=['function memberActiveDays(','function memberEffectiveWeight(','id=mjoin','joinDate,paidAmount','activeDays','effectiveWeight','Actual active days only','new joiner is charged only from the join date']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Join-date proration missing: '+', '.join(missing))
    app.write_text(s)
    print('Added join date and active-day month closing to',app)
