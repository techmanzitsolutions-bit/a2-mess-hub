from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    start=s.find('window.setMealSkip=async(meal,date)=>')
    end=s.find('window.cancelMealSkip=async', start)
    if start < 0 or end < 0:
        raise SystemExit('Meal skip handler not found')

    handler=r'''window.setMealSkip=async(meal,date)=>{
  if(state.profile?.role!=='member')return toast('Member only');
  if(!mealSkipOpen(date,meal))return toast('Skip cutoff has passed');
  const uid=auth.currentUser?.uid||'';
  if(!uid)return toast('Please login again');
  let member=state.data.members.find(m=>String(m.id||'')===String(state.profile.memberId||'')||String(m.uid||'')===String(uid));
  if(!member&&state.profile.memberId){
    try{const snap=await getDoc(doc(db,'members',state.profile.memberId));if(snap.exists())member={id:snap.id,...snap.data()}}catch(e){console.warn('member lookup failed',e)}
  }
  const memberId=member?.id||state.profile.memberId||uid;
  const memberName=member?.name||state.profile.name||auth.currentUser?.email||'Member';
  const id=`${uid}_${date}_${meal.toLowerCase()}`;
  const ref=doc(db,'mealSkips',id);
  try{
    await setDoc(ref,{uid,memberId,memberName,date,meal,status:'SKIPPED',cutoff:mealSkipCutoffs[meal],cutoffAt:mealCutoffDate(date,meal),createdAt:serverTimestamp(),updatedAt:serverTimestamp()},{merge:true});
    const verify=await getDoc(ref);
    if(!verify.exists())throw new Error('Cloud verification failed');
    const saved={id:verify.id,...verify.data()};
    const i=(state.data.mealSkips||[]).findIndex(x=>x.id===id);
    if(i>=0)state.data.mealSkips[i]=saved;else state.data.mealSkips=[...(state.data.mealSkips||[]),saved];
    render();
    toast(`${meal} skip saved to cloud ✅`);
    if(typeof openMealSkipNotifications==='function')openMealSkipNotifications(memberName,meal,date);
  }catch(e){
    console.error('Meal skip cloud save failed',e);
    toast('Meal skip NOT saved: '+(e?.message||e));
  }
}
'''
    s=s[:start]+handler+s[end:]

    # Make the member page explicitly show that a saved skip is cloud-synced.
    s=s.replace("${rec?'NO NEED':'NEED MEAL'}", "${rec?'NO NEED · CLOUD SAVED':'NEED MEAL'}")

    required=['Cloud verification failed','skip saved to cloud ✅','Meal skip NOT saved:','NO NEED · CLOUD SAVED']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Cloud write fix missing: '+', '.join(missing))

    app.write_text(s)
    print(f'Fixed and verified meal skip Firestore writes in {app}')
