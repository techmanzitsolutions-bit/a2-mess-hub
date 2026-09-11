from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    # Always keep mealSkips in state, even if an earlier build-time patch changed the state shape.
    if 'mealSkips:[]' not in s:
        state_markers=['monthlyClosings:[]','users:[]']
        done=False
        for marker in state_markers:
            if marker in s:
                s=s.replace(marker, marker+',mealSkips:[]', 1)
                done=True
                break
        if not done:
            raise SystemExit('Could not add mealSkips state')

    # A dedicated realtime listener is more reliable than depending on an exact collection-list replacement.
    listener="state.unsubs.push(onSnapshot(collection(db,'mealSkips'),snap=>{state.data.mealSkips=snap.docs.map(d=>({id:d.id,...d.data()}));render()},e=>{console.error('mealSkips realtime listener',e);toast('Meal skip sync error')}));"
    if "onSnapshot(collection(db,'mealSkips')" not in s:
        marker='function listen(){'
        if marker not in s:
            raise SystemExit('listen() not found')
        s=s.replace(marker, marker+listener, 1)

    # Add a visible live indicator to Admin/Chef Skip Meal view so they can confirm sync instantly.
    old='<div class=small>Live member skip count before cooking.</div>'
    new='<div class=small>Live member skip count before cooking. Updates automatically across member, chef and admin accounts.</div><div class=ok style="margin-top:8px">● LIVE SYNC · ${(state.data.mealSkips||[]).filter(x=>x.date===date&&x.status===\'SKIPPED\').length} skip(s) for ${date}</div>'
    if old in s and '● LIVE SYNC' not in s:
        s=s.replace(old,new,1)

    required=["onSnapshot(collection(db,'mealSkips')",'mealSkips:[]','● LIVE SYNC','Updates automatically across member, chef and admin accounts.']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Realtime meal skip fix missing: '+', '.join(missing))

    app.write_text(s)
    print(f'Ensured realtime meal skip sync in {app}')
