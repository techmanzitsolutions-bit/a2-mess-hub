from pathlib import Path

app = Path('/tmp/a2-pwa/www/app.html')
s = app.read_text()

def replace_between(text, start_marker, end_marker, replacement):
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f'Missing start marker: {start_marker}')
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f'Missing end marker: {end_marker}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# Payment/due helpers. Old payment records remain compatible: paidAmount falls back to amount.
helpers = r'''function planValue(v){const n=Number(String(v??'').replace(/[^0-9.]/g,''));return Number.isFinite(n)?n:0}
function paidValue(x){const n=Number(x?.paidAmount??x?.amount??0);return Number.isFinite(n)?n:0}
function memberKey(m){return String(m?.uid||m?.id||'')}
function paymentMatchesMember(p,m){const k=memberKey(m);return !!k&&String(p?.uid||'')===k}
function memberPaid(m,excludeId=''){return state.data.payments.reduce((sum,p)=>sum+((p.id!==excludeId&&paymentMatchesMember(p,m))?paidValue(p):0),0)}
function paymentStatus(plan,paid){const due=Math.max(0,plan-paid);return paid<=0?'DUE':due>0?'PARTIAL':'PAID'}
function memberSummary(m){const plan=planValue(m?.planAmount||m?.plan),paid=Math.max(0,memberPaid(m)),due=Math.max(0,plan-paid);return{plan,paid,due,status:paymentStatus(plan,paid)}}
function linkedMember(uid){return state.data.members.find(m=>memberKey(m)===String(uid||''))}
function paymentSummary(x){const m=linkedMember(x?.uid),plan=planValue(m?.planAmount||m?.plan||x?.planAmount||x?.plan),paid=m?memberPaid(m):paidValue(x),due=Math.max(0,plan-paid);return{plan,paid,due,status:paymentStatus(plan,paid)}}
function money(n){return Number(n||0).toFixed(2)}
'''
if 'function planValue(v)' not in s:
    s = s.replace('function dashboard(){', helpers + '\nfunction dashboard(){', 1)

# Make PARTIAL visually different while keeping DUE red.
if '.tag.partial{' not in s:
    s = s.replace('</style>', '.tag.partial{background:#f6cb67;color:#201600}\n</style>', 1)

dashboard = r'''function dashboard(){const paid=state.data.payments.reduce((a,x)=>a+paidValue(x),0),due=state.data.members.reduce((a,m)=>a+memberSummary(m).due,0),exp=state.data.expenses.reduce((a,x)=>a+Number(x.amount||0),0);return`<div class=grid>${metric('Members',state.data.members.length)}${metric('Collected','AED '+paid.toFixed(0))}${metric('Due','AED '+due.toFixed(0))}${metric('Expenses','AED '+exp.toFixed(0))}${metric('Balance','AED '+(paid-exp).toFixed(0))}</div>`}
'''
s = replace_between(s, 'function dashboard(){', 'function users(){', dashboard)

members = r'''function members(){return`<div class=top style="margin-top:14px"><p class=muted>Subscription members · payment status updates automatically</p>${state.profile.role==='admin'?'<button class=btn onclick=memberForm()>+ Member Record</button>':''}</div><div class="card list">${state.data.members.map(x=>{const sm=memberSummary(x);return`<div class=row><span><b>${esc(x.name)}</b><small class=muted> · Plan AED ${money(sm.plan)}</small></span><span>Paid AED ${money(sm.paid)}<br><small class=muted>Due AED ${money(sm.due)}</small></span><span class="tag ${sm.status==='DUE'?'due':sm.status==='PARTIAL'?'partial':''}">${sm.status}</span><span>${state.profile.role==='admin'?`<div class=actions><button class=ghost onclick="memberFormById('${x.id}')">Edit</button><button class="ghost danger" onclick="delRecord('members','${x.id}','member')">Delete</button></div>`:''}</span></div>`}).join('')}</div>`}
window.memberForm=(x={})=>{const sm=x.id?memberSummary(x):{plan:planValue(x.plan||'AED 200'),paid:0,due:planValue(x.plan||'AED 200'),status:'DUE'};modal(`<div class=top><h3>Member</h3><button class=ghost onclick=closeM()>✕</button></div><div class=form><div class=field><label>Name</label><input id=mname value="${esc(x.name||'')}"></div><div class=field><label>Plan</label><select id=mplan><option ${sm.plan===100?'selected':''}>AED 100</option><option ${sm.plan===200?'selected':''}>AED 200</option><option ${sm.plan===250?'selected':''}>AED 250</option></select></div><div class=field><label>Payment Status</label><input value="${sm.status}" readonly></div><div class=field><label>Paid / Due</label><input value="AED ${money(sm.paid)} paid · AED ${money(sm.due)} due" readonly></div><div class=field><label>Phone</label><input id=mphone value="${esc(x.phone||'')}"></div><div class=span2><button class=btn onclick="saveMember('${x.id||''}')">SAVE</button></div></div>`)};
window.memberFormById=id=>memberForm(state.data.members.find(x=>x.id===id)||{});
window.saveMember=async id=>{try{const old=state.data.members.find(x=>x.id===id)||{},plan=$('mplan').value,planAmount=planValue(plan),probe={id,uid:old.uid,name:$('mname').value.trim(),plan,planAmount},paid=id?memberPaid({...old,...probe}):0,due=Math.max(0,planAmount-paid),status=paymentStatus(planAmount,paid),v={name:$('mname').value.trim(),plan,planAmount,paidAmount:paid,dueAmount:due,status,phone:$('mphone').value.trim(),updatedAt:serverTimestamp()};if(!v.name)return toast('Enter member name');id?await updateDoc(doc(db,'members',id),v):await addDoc(collection(db,'members'),{...v,createdAt:serverTimestamp()});closeM();toast('Member saved · '+status)}catch(e){err(e)}};
'''
s = replace_between(s, 'function members(){', 'function meals(){', members)

payments = r'''function payments(){const rows=state.profile.role==='member'?state.data.payments.filter(x=>x.uid===auth.currentUser.uid):state.data.payments;return`<div class=top style="margin-top:14px"><p class=muted>Plan / paid / due amounts calculate automatically</p>${state.profile.role==='admin'?'<button class=btn onclick=paymentForm()>+ Payment</button>':''}</div><div class="card list">${rows.map(x=>{const ps=paymentSummary(x),entryPaid=paidValue(x);return`<div class=row><span><b>${esc(x.name||linkedMember(x.uid)?.name||'Member')}</b><small class=muted> · Plan AED ${money(ps.plan)}</small></span><span>Paid AED ${money(ps.paid)}<br><small class=muted>Due AED ${money(ps.due)}${ps.paid!==entryPaid?' · Entry AED '+money(entryPaid):''}</small></span><span class="tag ${ps.status==='DUE'?'due':ps.status==='PARTIAL'?'partial':''}">${ps.status}</span><span>${state.profile.role==='admin'?`<div class=actions><button class=ghost onclick="paymentFormById('${x.id}')">Edit</button><button class=ghost onclick="waDue('${esc(x.phone||linkedMember(x.uid)?.phone||'')}','${esc(x.name||linkedMember(x.uid)?.name||'Member')}',${ps.plan},${ps.paid},${ps.due})">WhatsApp</button><button class="ghost danger" onclick="delRecord('payments','${x.id}','payment')">Delete</button></div>`:''}</span></div>`}).join('')}</div>`}
window.paymentForm=(x={})=>{const m=linkedMember(x.uid),plan=planValue(m?.planAmount||m?.plan||x.planAmount||200),current=paidValue(x);modal(`<div class=top><h3>${x.id?'Edit':'Add'} Payment</h3><button class=ghost onclick=closeM()>✕</button></div><div class=form><div class=field><label>Member</label><select id=puid onchange="syncPaymentMember()"><option value="">Manual / Not linked</option>${state.data.members.map(mm=>`<option value="${memberKey(mm)}" ${(x.uid===memberKey(mm))?'selected':''}>${esc(mm.name)}</option>`).join('')}</select></div><div class=field><label>Name</label><input id=pname value="${esc(x.name||m?.name||'')}"></div><div class=field><label>Phone</label><input id=pphone value="${esc(x.phone||m?.phone||'')}" placeholder="9715..."></div><div class=field><label>Plan Amount</label><input id=pplan type=number min=0 step=.01 value="${plan}" oninput="recalcPayment()"></div><div class=field><label>Paid Amount (this entry)</label><input id=ppaid type=number min=0 step=.01 value="${current}" oninput="recalcPayment()"></div><div class=field><label>Due Amount</label><input id=pdue readonly></div><div class=field><label>Status</label><input id=pstatus readonly></div><div class=span2><div class=note>Example: Plan AED 200 + Paid AED 80 = Due AED 120 · PARTIAL</div></div><div class=span2><button class=btn onclick="savePayment('${x.id||''}')">SAVE</button></div></div>`);recalcPayment('${x.id||''}')};
window.paymentFormById=id=>paymentForm(state.data.payments.find(x=>x.id===id)||{});
window.syncPaymentMember=()=>{const m=linkedMember($('puid')?.value);if(m){$('pname').value=m.name||'';$('pphone').value=m.phone||'';$('pplan').value=planValue(m.planAmount||m.plan)}recalcPayment()};
window.recalcPayment=(editId='')=>{const plan=Math.max(0,Number($('pplan')?.value||0)),entry=Math.max(0,Number($('ppaid')?.value||0)),m=linkedMember($('puid')?.value),other=m?memberPaid(m,editId):0,total=Math.max(0,other+entry),due=Math.max(0,plan-total),status=paymentStatus(plan,total);if($('pdue'))$('pdue').value='AED '+money(due);if($('pstatus'))$('pstatus').value=status};
window.savePayment=async id=>{try{const uid=$('puid').value,m=linkedMember(uid),plan=Math.max(0,Number($('pplan').value||0)),entry=Math.max(0,Number($('ppaid').value||0));if(plan<=0)return toast('Enter plan amount');const other=m?memberPaid(m,id):0,total=other+entry;if(total>plan)return toast('Paid amount cannot exceed plan amount');const due=Math.max(0,plan-total),status=paymentStatus(plan,total),v={uid,name:$('pname').value.trim()||m?.name||'',phone:$('pphone').value.trim()||m?.phone||'',planAmount:plan,paidAmount:entry,amount:entry,dueAmount:due,status,updatedAt:serverTimestamp()};let paymentId=id;if(id)await updateDoc(doc(db,'payments',id),v);else{const r=await addDoc(collection(db,'payments'),{...v,createdAt:serverTimestamp()});paymentId=r.id}if(m){await updateDoc(doc(db,'members',m.id),{plan:'AED '+plan,planAmount:plan,paidAmount:total,dueAmount:due,status,updatedAt:serverTimestamp()})}closeM();toast('Payment saved · Paid AED '+money(total)+' · Due AED '+money(due))}catch(e){err(e)}};
window.waDue=(phone,name,plan,paid,due)=>{const status=paymentStatus(Number(plan),Number(paid)),text=encodeURIComponent(`A2 MESS HUB\nHi ${name}, payment update:\nPlan: AED ${money(plan)}\nPaid: AED ${money(paid)}\nDue: AED ${money(due)}\nStatus: ${status}\n— Powered by TECHMANZ`);window.open(`https://wa.me/${String(phone||'').replace(/\D/g,'')}?text=${text}`,'_blank')};
'''
s = replace_between(s, 'function payments(){', 'window.delRecord=', payments)

reports = r'''function reports(){const paid=state.data.payments.reduce((a,x)=>a+paidValue(x),0),due=state.data.members.reduce((a,m)=>a+memberSummary(m).due,0),exp=state.data.expenses.reduce((a,x)=>a+Number(x.amount||0),0);return`<div class="grid">${metric('Income','AED '+paid.toFixed(2))}${metric('Outstanding','AED '+due.toFixed(2))}${metric('Expense','AED '+exp.toFixed(2))}${metric('Net','AED '+(paid-exp).toFixed(2))}</div>`}
'''
s = replace_between(s, 'function reports(){', 'function settings(){', reports)

app.write_text(s)
print('Applied AED 100 plan + automatic paid/due/PARTIAL calculation patch')
