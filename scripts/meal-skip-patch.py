from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    # Realtime state + listener for meal skip requests.
    s=s.replace("users:[],monthlyClosings:[]}","users:[],monthlyClosings:[],mealSkips:[]}")
    s=s.replace("['members','inventory','meals','expenses','payments'].forEach", "['members','inventory','meals','expenses','payments','mealSkips'].forEach")

    # Navigation for all roles. Members use it to skip; Chef/Admin use it for cooking counts.
    nav_replacements={
      "['dashboard','users','members','meals','inventory','expenses','payments','gas','closing','reports','backup','settings']":"['dashboard','users','members','meals','skipmeal','inventory','expenses','payments','gas','closing','reports','backup','settings']",
      "['dashboard','users','members','meals','inventory','expenses','payments','closing','reports','backup','settings']":"['dashboard','users','members','meals','skipmeal','inventory','expenses','payments','closing','reports','backup','settings']",
      "['dashboard','meals','inventory','expenses','gas','settings']":"['dashboard','meals','skipmeal','inventory','expenses','gas','settings']",
      "['dashboard','meals','inventory','expenses','settings']":"['dashboard','meals','skipmeal','inventory','expenses','settings']",
      "['dashboard','meals','payments','expenses','gas','settings']":"['dashboard','meals','skipmeal','payments','expenses','gas','settings']",
      "['dashboard','meals','payments','gas','settings']":"['dashboard','meals','skipmeal','payments','gas','settings']",
      "['dashboard','meals','payments','expenses','settings']":"['dashboard','meals','skipmeal','payments','expenses','settings']",
      "['dashboard','meals','payments','settings']":"['dashboard','meals','skipmeal','payments','settings']",
    }
    for old,new in nav_replacements.items():
        s=s.replace(old,new)

    if "skipmeal:'Skip Meal'" not in s:
        s=s.replace("meals:'Meals',", "meals:'Meals',skipmeal:'Skip Meal',", 1)

    if 'function mealSkipPage(){' not in s:
        marker='function reports(){'
        if marker not in s:
            raise SystemExit('reports marker not found')
        code=r'''const mealSkipCutoffs={Breakfast:'06:00',Lunch:'10:00',Dinner:'17:00'};
function uaeClock(){const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Dubai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));return{date:`${p.year}-${p.month}-${p.day}`,minutes:Number(p.hour)*60+Number(p.minute)}}
function uaeDateKey(offset=0){const p=uaeClock(),[y,m,d]=p.date.split('-').map(Number),x=new Date(Date.UTC(y,m-1,d+offset));return`${x.getUTCFullYear()}-${String(x.getUTCMonth()+1).padStart(2,'0')}-${String(x.getUTCDate()).padStart(2,'0')}`}
function mealCutoffDate(date,meal){return new Date(`${date}T${mealSkipCutoffs[meal]}:00+04:00`)}
function mealSkipOpen(date,meal){const now=uaeClock();if(date>now.date)return true;if(date<now.date)return false;const[h,m]=mealSkipCutoffs[meal].split(':').map(Number);return now.minutes<(h*60+m)}
function activeMessMembers(){return state.data.members.filter(m=>m.active!==false)}
function skipFor(uid,date,meal){return(state.data.mealSkips||[]).find(x=>String(x.uid||'')===String(uid||'')&&x.date===date&&x.meal===meal&&x.status==='SKIPPED')||null}
function skipsFor(date,meal){return(state.data.mealSkips||[]).filter(x=>x.date===date&&x.meal===meal&&x.status==='SKIPPED')}
function cookingCount(date,meal){const total=activeMessMembers().length,ids=new Set(skipsFor(date,meal).map(x=>x.memberId||x.uid));return{total,skipped:ids.size,cook:Math.max(0,total-ids.size)}}
function mealSkipPage(){const role=state.profile.role,date=window._mealSkipDate||uaeDateKey(0);if(role==='member'){const member=state.data.members.find(m=>String(m.id||'')===String(state.profile.memberId||'')||String(m.uid||'')===String(auth.currentUser?.uid||'')),uid=auth.currentUser?.uid||'';return`<div class=card style="margin-top:14px"><div class=top><div><h3 style="margin:0">🍽️ No Need / Skip Meal</h3><div class=small>Tell the kitchen before cooking so food quantity can be reduced.</div></div><span class=tag>${esc(member?.name||state.profile.name||'Member')}</span></div><div class=form style="margin-top:14px"><div class=field><label>Date</label><input type=date min="${uaeDateKey(0)}" value="${date}" onchange="window._mealSkipDate=this.value;render()"></div><div class=field><label>Quick select</label><div class=actions><button class=ghost onclick="window._mealSkipDate='${uaeDateKey(0)}';render()">Today</button><button class=ghost onclick="window._mealSkipDate='${uaeDateKey(1)}';render()">Tomorrow</button></div></div></div><div class=grid style="margin-top:14px">${['Breakfast','Lunch','Dinner'].map(meal=>{const rec=skipFor(uid,date,meal),open=mealSkipOpen(date,meal);return`<div class=card><b>${meal}</b><div class=small>Cutoff ${mealSkipCutoffs[meal]}</div><div style="margin:12px 0"><span class="tag ${rec?'due':''}">${rec?'NO NEED':'NEED MEAL'}</span></div>${rec&&open?`<button class=ghost onclick="cancelMealSkip('${rec.id}','${meal}','${date}')">Cancel Skip</button>`:!rec&&open?`<button class=btn onclick="setMealSkip('${meal}','${date}')">NO NEED / SKIP</button>`:`<div class=note>Kitchen preparation started – skip closed.</div>`}</div>`}).join('')}</div><div class=note style="margin-top:12px">Skip Meal changes cooking quantity only. It does not reduce your monthly payment or expense share.</div></div>`}
const rows=['Breakfast','Lunch','Dinner'].map(meal=>{const c=cookingCount(date,meal);return`<div class=card><b>${meal}</b><div class=metric>${c.cook}</div><div class=small>Cook for ${c.cook} · ${c.skipped} skipped · ${c.total} members</div><div class=small>Cutoff ${mealSkipCutoffs[meal]}</div></div>`}).join(''),list=(state.data.mealSkips||[]).filter(x=>x.date===date&&x.status==='SKIPPED').sort((a,b)=>String(a.meal).localeCompare(String(b.meal)));return`<div class=card style="margin-top:14px"><div class=top><div><h3 style="margin:0">👨‍🍳 Kitchen Meal Count</h3><div class=small>Live member skip count before cooking.</div></div><span class=tag>${role.toUpperCase()}</span></div><div class=form style="margin-top:14px"><div class=field><label>Date</label><input type=date value="${date}" onchange="window._mealSkipDate=this.value;render()"></div><div class=field><label>Quick select</label><div class=actions><button class=ghost onclick="window._mealSkipDate='${uaeDateKey(0)}';render()">Today</button><button class=ghost onclick="window._mealSkipDate='${uaeDateKey(1)}';render()">Tomorrow</button></div></div></div><div class=grid style="margin-top:14px">${rows}</div></div><div class=card style="margin-top:14px"><h3 style="margin-top:0">Skipped Members</h3><div class=list>${list.map(x=>`<div class=row><span><b>${esc(x.memberName||'Member')}</b></span><span>${esc(x.meal)}</span><span class=tag>NO NEED</span><span>${role==='admin'?`<button class="ghost danger" onclick="adminDeleteMealSkip('${x.id}')">Remove</button>`:''}</span></div>`).join('')||'<p class=muted>No meal skips for this date.</p>'}</div></div>`}
window.setMealSkip=async(meal,date)=>{if(state.profile?.role!=='member')return toast('Member only');if(!mealSkipOpen(date,meal))return toast('Skip cutoff has passed');const uid=auth.currentUser?.uid||'',member=state.data.members.find(m=>String(m.id||'')===String(state.profile.memberId||'')||String(m.uid||'')===String(uid));if(!uid||!member)return toast('Member account is not linked');const id=`${uid}_${date}_${meal.toLowerCase()}`;try{await setDoc(doc(db,'mealSkips',id),{uid,memberId:member.id,memberName:member.name||state.profile.name||'Member',date,meal,status:'SKIPPED',cutoff:mealSkipCutoffs[meal],cutoffAt:mealCutoffDate(date,meal),createdAt:serverTimestamp(),updatedAt:serverTimestamp()},{merge:true});toast(`${meal} marked No Need`)}catch(e){err(e)}}
window.cancelMealSkip=async(id,meal,date)=>{if(!mealSkipOpen(date,meal))return toast('Skip cutoff has passed');try{await deleteDoc(doc(db,'mealSkips',id));toast(`${meal} skip cancelled`)}catch(e){err(e)}}
window.adminDeleteMealSkip=async id=>{if(state.profile?.role!=='admin')return toast('Admin only');if(!ask('Remove this meal skip?'))return;try{await deleteDoc(doc(db,'mealSkips',id));toast('Meal skip removed')}catch(e){err(e)}}
'''
        s=s.replace(marker,code+marker,1)

    renderer_replacements={
      "{dashboard,users,members,meals,inventory,expenses,payments,gas:gasOrder,closing:monthClosePage,reports,backup:backupPage,settings}":"{dashboard,users,members,meals,skipmeal:mealSkipPage,inventory,expenses,payments,gas:gasOrder,closing:monthClosePage,reports,backup:backupPage,settings}",
      "{dashboard,users,members,meals,inventory,expenses,payments,closing:monthClosePage,reports,backup:backupPage,settings}":"{dashboard,users,members,meals,skipmeal:mealSkipPage,inventory,expenses,payments,closing:monthClosePage,reports,backup:backupPage,settings}",
    }
    for old,new in renderer_replacements.items():
        s=s.replace(old,new)

    # Generic fallback if renderer is role-agnostic and already contains meal page map.
    if 'skipmeal:mealSkipPage' not in s:
        needle='{dashboard,users,members,meals,inventory,expenses,payments,'
        if needle in s:
            s=s.replace(needle,'{dashboard,users,members,meals,skipmeal:mealSkipPage,inventory,expenses,payments,',1)

    required=['mealSkips','function mealSkipPage(){','window.setMealSkip=async','window.cancelMealSkip=async',"skipmeal:'Skip Meal'",'skipmeal:mealSkipPage','Kitchen Meal Count','NO NEED / SKIP','Kitchen preparation started – skip closed.','Skip Meal changes cooking quantity only']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Meal skip patch missing: '+', '.join(missing))
    app.write_text(s)
    print(f'Added member meal skip and kitchen cooking counts to {app}')
