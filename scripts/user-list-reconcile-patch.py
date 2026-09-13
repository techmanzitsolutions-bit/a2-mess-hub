from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    s=app.read_text()

    start=s.find('function users(){')
    end=s.find('\nwindow.userForm=',start)
    if start<0 or end<0:
        raise SystemExit('users() block not found')

    new=r'''function userRows(){const byUid=new Map();state.data.users.forEach(u=>{const uid=String(u.uid||u.id||'');if(uid)byUid.set(uid,{...u,_source:'profile'})});state.data.members.forEach(m=>{const uid=String(m.uid||'').trim();if(!uid)return;const current=byUid.get(uid);if(current){byUid.set(uid,{...current,memberId:current.memberId||m.id,name:current.name||m.name,email:current.email||m.email||'',_linkedMemberId:m.id});return}byUid.set(uid,{id:uid,uid,name:m.name||'Member',email:m.email||'',role:'member',active:m.active!==false,memberId:m.id,_source:'member-fallback',_linkedMemberId:m.id})});return [...byUid.values()].sort((a,b)=>String(a.name||a.email||'').localeCompare(String(b.name||b.email||'')))}
function users(){const rows=userRows();return`<div class=top style="margin-top:14px"><div><p class=muted style="margin:0">All app logins and linked member accounts</p><div class=small>${rows.length} account(s) visible</div></div><div class=actions><button class=ghost onclick=repairLinkedUsers()>Sync User List</button><button class=btn onclick=userForm()>+ Create User</button></div></div><div class="card list">${rows.map(u=>{const lm=linkedMemberForUser(u);const fallback=u._source==='member-fallback';return`<div class=row><span><b>${esc(u.name||lm?.name||'User')}</b><small class=muted> · ${esc(u.email||lm?.email||'No email')}</small>${lm?`<small class=muted> · Linked: ${esc(lm.name)}</small>`:''}${fallback?'<small class=muted> · Linked account detected</small>':''}</span><span>${esc(u.role||'member')}</span><span>${u.active===false?'Disabled':'Active'}</span><span>${u.role!=='admin'?`<div class=actions>${fallback?`<button class=btn onclick="repairOneLinkedUser('${esc(u.uid||u.id)}')">Repair</button>`:`<button class=ghost onclick="editUser('${u.id}')">Edit</button><button class=ghost onclick="resetUser('${esc(u.email||'')}')">Reset Password</button><button class=ghost onclick="toggleUser('${u.id}',${u.active===false})">${u.active===false?'Enable':'Disable'}</button><button class="ghost danger" onclick="removeUserProfile('${u.id}')">Remove</button>`}</div>`:''}</span></div>`}).join('')||'<p class=muted>No user accounts found.</p>'}</div><div class=note style="margin-top:12px">The Users page now combines Firestore user profiles with linked Member records, so an existing login cannot disappear from this list just because its profile/link data is incomplete.</div>`}
window.repairOneLinkedUser=async uid=>{try{const m=state.data.members.find(x=>String(x.uid||'')===String(uid));if(!m)return toast('Linked member not found');const ref=doc(db,'users',uid),snap=await getDoc(ref),old=snap.exists()?snap.data():{};await setDoc(ref,{uid,name:old.name||m.name||'Member',email:old.email||m.email||'',role:old.role||'member',memberId:old.memberId||m.id,active:old.active!==false,updatedAt:serverTimestamp(),...(snap.exists()?{}:{createdAt:serverTimestamp()})},{merge:true});await updateDoc(doc(db,'members',m.id),{uid,email:old.email||m.email||'',updatedAt:serverTimestamp()});toast((m.name||'User')+' synced to Users list ✅')}catch(e){err(e)}};
window.repairLinkedUsers=async()=>{try{const linked=state.data.members.filter(m=>String(m.uid||'').trim());if(!linked.length)return toast('No linked member accounts found');let repaired=0;for(const m of linked){const uid=String(m.uid),ref=doc(db,'users',uid),snap=await getDoc(ref),old=snap.exists()?snap.data():{};await setDoc(ref,{uid,name:old.name||m.name||'Member',email:old.email||m.email||'',role:old.role||'member',memberId:old.memberId||m.id,active:old.active!==false,updatedAt:serverTimestamp(),...(snap.exists()?{}:{createdAt:serverTimestamp()})},{merge:true});repaired++}toast('User list synced · '+repaired+' linked account(s) checked ✅')}catch(e){err(e)}};
'''
    s=s[:start]+new+s[end:]

    # Add an error callback and stable sorting to the users realtime listener when present.
    old="onSnapshot(collection(db,'users'),x=>{state.data.users=x.docs.map(d=>({id:d.id,...d.data()}));render()},err)"
    new_listener="onSnapshot(collection(db,'users'),x=>{state.data.users=x.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>String(a.name||a.email||'').localeCompare(String(b.name||b.email||'')));render()},err)"
    if old in s:
        s=s.replace(old,new_listener,1)
    old2="onSnapshot(collection(db,'users'),s=>{state.data.users=s.docs.map(d=>({id:d.id,...d.data()}));render()})"
    if old2 in s:
        s=s.replace(old2,"onSnapshot(collection(db,'users'),s=>{state.data.users=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>String(a.name||a.email||'').localeCompare(String(b.name||b.email||'')));render()},err)",1)

    required=['function userRows()','Sync User List','window.repairLinkedUsers=async','window.repairOneLinkedUser=async','Linked account detected']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('User list reconciliation patch missing: '+', '.join(missing))
    app.write_text(s)
    print('Applied user list reconciliation to',app)
