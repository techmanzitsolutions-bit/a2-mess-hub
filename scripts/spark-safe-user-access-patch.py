from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]: paths=[Path('www/app.html')]

for app in paths:
    s=app.read_text()
    cleanup="state.unsubs.forEach(f=>f());state.unsubs=[];"
    meal="state.unsubs.push(onSnapshot(collection(db,'mealSkips'),snap=>{state.data.mealSkips=snap.docs.map(d=>({id:d.id,...d.data()}));render()},e=>{console.error('mealSkips realtime listener',e);toast('Meal skip sync error')}));"
    guard="state.unsubs.push(onSnapshot(doc(db,'users',auth.currentUser.uid),async snap=>{if(window._accessClosing)return;const p=snap.data();if(!snap.exists()||p.active===false||p.removed===true){window._accessClosing=true;toast('Account disabled or removed by Admin');await signOut(auth);return}state.profile={uid:snap.id,...p};render()},err));"
    misplaced="function listen(){"+meal+cleanup
    if 'Account disabled or removed by Admin' not in s:
        if misplaced in s:s=s.replace(misplaced,"function listen(){"+cleanup+meal+guard,1)
        elif "function listen(){"+cleanup in s:s=s.replace("function listen(){"+cleanup,"function listen(){"+cleanup+guard,1)
        else:raise SystemExit('Realtime listener marker missing')

    marker='function render(){'
    overrides=r'''
window.toggleUser=async(id,isDisabled)=>{try{await updateDoc(doc(db,'users',id),{active:isDisabled,removed:false,updatedAt:serverTimestamp()});toast(isDisabled?'User access restored':'User disabled and signed out')}catch(e){err(e)}};
window.removeUserProfile=async id=>{if(!ask('Remove this user’s app access? The Firebase login will remain reserved, but it will not be able to read or change app data.'))return;try{const u=state.data.users.find(x=>x.id===id),m=linkedMemberForUser(u),b=writeBatch(db);b.set(doc(db,'users',id),{active:false,removed:true,removedAt:serverTimestamp(),removedBy:auth.currentUser.uid},{merge:true});if(m)b.update(doc(db,'members',m.id),{uid:'',loginEmail:'',updatedAt:serverTimestamp()});await b.commit();toast('User app access removed on all devices')}catch(e){err(e)}};
'''
    if 'User app access removed on all devices' not in s:
        if marker not in s:raise SystemExit('Render marker missing')
        s=s.replace(marker,overrides+'\n'+marker,1)
    s=s.replace("if(!p.exists()||p.data().active===false)","if(!p.exists()||p.data().active===false||p.data().removed===true)",1)
    required=['Account disabled or removed by Admin','User disabled and signed out','User app access removed on all devices','removed:true']
    missing=[x for x in required if x not in s]
    if missing:raise SystemExit('Spark access hardening missing: '+', '.join(missing))
    app.write_text(s)
    print('Applied Spark-safe user access hardening to',app)
