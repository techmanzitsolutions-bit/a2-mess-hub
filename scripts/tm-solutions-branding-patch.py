from pathlib import Path
import re, sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

BRAND='''<div class="powered tm-powered" style="margin-top:22px;display:grid;justify-items:center;gap:5px;color:#7f9d91;font-size:9px;letter-spacing:.08em;text-transform:uppercase"><span>Powered by</span><img src="./tm-solutions-logo.webp" alt="TM Solutions" style="width:116px;max-width:88%;height:auto;display:block;filter:drop-shadow(0 0 8px rgba(38,160,255,.30))"></div>'''

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    old='<p class=powered style="margin-top:26px">⚡ TECHMANZ</p>'
    if old in s:
        s=s.replace(old,BRAND)
    else:
        s,n=re.subn(r'<p class=["\']?powered["\']?[^>]*>.*?</p>',BRAND,s,count=1,flags=re.S)
        if n==0 and 'tm-solutions-logo.webp' not in s:
            raise SystemExit('Powered-by branding marker not found')
    if 'tm-solutions-logo.webp' not in s or 'Powered by' not in s:
        raise SystemExit('TM Solutions branding was not applied')
    app.write_text(s)
    print('Applied TM Solutions powered-by branding to',app)
