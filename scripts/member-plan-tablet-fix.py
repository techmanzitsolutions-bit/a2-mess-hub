from pathlib import Path
import sys

paths = [Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths = [Path('www/app.html')]

decode = lambda x: x.replace('§', chr(96)).replace('¤', chr(36))

MEMBER_FORM = decode(r'''window.memberForm=(x={})=>{const q=x.id?memberSummary(x):{plan:planValue(x.plan||'AED 200'),paid:0,due:planValue(x.plan||'AED 200'),status:'DUE'},joinDate=String(x.joinDate||(!x.id?new Date().toISOString().slice(0,10):'')).slice(0,10),selectedPlan=[100,200,250].includes(Number(q.plan))?Number(q.plan):200;modal(§<div class=top><h3>¤{x.id?'Edit':'Add'} Member</h3><button type=button class=ghost onclick=closeM()>✕</button></div><div class=form><div class=field><label>Name</label><input id=mname value="¤{esc(x.name||'')}"></div><div class=field><label>Monthly Plan</label><input id=mplan type=hidden value="AED ¤{selectedPlan}"><div class=plan-choice role=group aria-label="Monthly plan">¤{[100,200,250].map(v=>§<button type=button class="ghost plan-option ¤{selectedPlan===v?'selected':''}" data-plan="¤{v}" onclick="selectMemberPlan(¤{v},this)">AED ¤{v}</button>§).join('')}</div><small class=muted>Choose one plan only</small></div><div class=field><label>Join Date</label><input id=mjoin type=date value="¤{esc(joinDate)}"></div><div class=field><label>First Month Calculation</label><input value="Actual active days only" readonly></div><div class=field><label>¤{currentBillingMonth()} Status</label><input value="¤{q.status}" readonly></div><div class=field><label>Paid / Due</label><input value="AED ¤{money(q.paid)} paid · AED ¤{money(q.due)} due" readonly></div><div class=field><label>Phone</label><input id=mphone inputmode=tel value="¤{esc(x.phone||'')}"></div><div class="span2 note">Join day is included. At month-end, this member receives only the expense share for active days. Any extra payment becomes next-month advance; any shortage becomes due.</div><div class=span2><button id=memberSaveBtn type=button class=btn onclick="saveMember('¤{x.id||''}')">SAVE MEMBER</button></div></div>§)};
window.selectMemberPlan=(value,button)=>{const amount=Number(value);if(![100,200,250].includes(amount))return;const input=¤('mplan');if(input)input.value='AED '+amount;document.querySelectorAll('.plan-option').forEach(x=>x.classList.toggle('selected',x===button));};''')

SAVE_MEMBER = r'''window.saveMember=async id=>{const btn=$('memberSaveBtn');if(btn?.disabled)return;try{const old=state.data.members.find(x=>x.id===id)||{},planAmount=planValue($('mplan')?.value),plan='AED '+planAmount;if(![100,200,250].includes(planAmount))return toast('Choose AED 100, AED 200 or AED 250');const name=$('mname')?.value.trim()||'',joinDate=$('mjoin')?.value||'',phone=$('mphone')?.value.trim()||'';if(!name)return toast('Enter member name');if(!joinDate&&!id)return toast('Select join date');if(btn){btn.disabled=true;btn.textContent='SAVING…'}const probe={...old,id:id||old.id,plan,planAmount},q=id?memberSummary(probe):{paid:0,due:planAmount,status:'DUE'},v={name,plan,planAmount,joinDate,paidAmount:q.paid,dueAmount:Math.max(0,planAmount-q.paid),status:paymentStatus(planAmount,q.paid),currentBillingMonth:currentBillingMonth(),phone,updatedAt:serverTimestamp()};if(id)await updateDoc(doc(db,'members',id),v);else await addDoc(collection(db,'members'),{...v,createdAt:serverTimestamp()});closeM();toast('Member saved · Plan AED '+planAmount)}catch(e){err(e)}finally{if(btn&&document.body.contains(btn)){btn.disabled=false;btn.textContent='SAVE MEMBER'}}};'''

CSS = r'''<style id="a2-member-plan-tablet-fix">
.plan-choice{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:5px}.plan-option{min-height:48px;padding:10px 6px;touch-action:manipulation}.plan-option.selected{background:linear-gradient(135deg,#10b981,#047857);border-color:#5ee7b7;color:#fff;box-shadow:0 0 0 2px #34d39944}.btn:disabled{opacity:.65;cursor:wait}
@media(max-width:520px){.plan-choice{gap:6px}.plan-option{font-size:14px}}
</style>'''


def replace_between(s, start, end, replacement):
    a = s.find(start)
    b = s.find(end, a)
    if a < 0 or b < 0:
        raise SystemExit(f'Markers missing: {start} / {end}')
    return s[:a] + replacement + s[b:]


for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s = app.read_text()
    s = replace_between(s, 'window.memberForm=', '\nwindow.memberFormById=', MEMBER_FORM)
    s = replace_between(s, 'window.saveMember=', '\nfunction meals(){', SAVE_MEMBER)
    if 'id="a2-member-plan-tablet-fix"' not in s:
        s = s.replace('</head>', CSS + '</head>')
    required = ['plan-choice', 'selectMemberPlan', 'data-plan=', "[100,200,250].includes(planAmount)", 'memberSaveBtn', 'SAVING…']
    missing = [x for x in required if x not in s]
    if missing:
        raise SystemExit('Member plan tablet fix missing: ' + ', '.join(missing))
    app.write_text(s)
    print('Added fixed plan choices and tablet-safe member save:', app)
