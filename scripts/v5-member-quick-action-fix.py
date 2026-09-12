from pathlib import Path
import sys
paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]: paths=[Path('www/app.html')]
for app in paths:
    s=app.read_text()
    marker='<button class=ghost onclick=logout()>Logout</button>'
    quick='<!-- MEAL SKIP QUICK ACTION -->${state.profile.role===\'member\'?`<button class=btn onclick="go(\'skipmeal\')">🍽️ Skip Meal</button>`:\'\'}'+marker
    if 'MEAL SKIP QUICK ACTION' not in s:
        if marker not in s: raise SystemExit('V5 logout marker not found')
        s=s.replace(marker,quick,1)
    app.write_text(s)
    print('Restored member meal skip quick action in V5 shell')
