from pathlib import Path
import sys,re

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]: paths=[Path('www/app.html')]

CSS=r'''
<style id="a2-premium-settings">
.page-settings{max-width:1120px!important}.settings-hero{display:grid;grid-template-columns:160px 1fr;gap:24px;align-items:center;padding:24px!important}.settings-logo{width:140px;height:140px;border-radius:28px;background:linear-gradient(145deg,#0d3427,#061812);border:1px solid rgba(76,227,161,.22);display:grid;place-items:center;overflow:hidden;box-shadow:inset 0 0 32px rgba(77,227,161,.05)}.settings-logo img{width:112px;height:112px;object-fit:contain}.settings-title{font-size:28px;font-weight:900;letter-spacing:-.03em}.settings-tagline{color:var(--muted);font-size:15px;margin-top:4px}.settings-meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:18px}.settings-meta>div{padding:12px 14px;border-radius:12px;background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06)}.settings-meta b{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8eaaa0;margin-bottom:5px}.settings-meta span{font-weight:750}.settings-list{display:grid;gap:10px;margin-top:14px}.settings-item{display:grid;grid-template-columns:46px 1fr auto;align-items:center;gap:14px;padding:15px 16px;border-radius:16px;background:linear-gradient(180deg,rgba(15,45,34,.86),rgba(8,27,20,.92));border:1px solid rgba(94,222,166,.13);box-shadow:0 10px 28px rgba(0,0,0,.13)}.settings-icon{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;background:rgba(53,217,145,.11);font-size:21px}.settings-item strong{display:block;font-size:16px}.settings-item small{display:block;color:var(--muted);margin-top:3px}.settings-arrow{font-size:26px;color:#aac4b9}.settings-brand{text-align:center;margin-top:14px;padding:20px!important}.settings-brand .crown{font-size:24px}.settings-brand h3{margin:5px 0}.settings-brand .powered{margin:14px 0 0!important}.settings-note{color:var(--muted);font-size:12px;margin-top:6px}
.bottom{gap:2px!important;overflow-x:auto!important;scrollbar-width:none!important;justify-content:flex-start!important;padding:6px!important}.bottom::-webkit-scrollbar{display:none}.bottom button{min-width:72px!important;display:grid!important;place-items:center!important;gap:2px!important;flex:0 0 auto!important}.bottom .navico{font-size:17px;line-height:1}.bottom .navtxt{font-size:10px;white-space:nowrap}.bottom button.on{background:rgba(77,227,161,.10)!important;border-radius:12px!important;color:#64efad!important}
@media(max-width:620px){.settings-hero{grid-template-columns:92px 1fr;gap:14px;padding:16px!important}.settings-logo{width:88px;height:88px;border-radius:20px}.settings-logo img{width:74px;height:74px}.settings-title{font-size:22px}.settings-meta{grid-template-columns:1fr 1fr}.settings-meta>div:last-child{grid-column:1/-1}.settings-item{padding:13px}.settings-icon{width:42px;height:42px}.page-settings .top h2{font-size:30px!important}}
</style>
'''

for app in paths:
    if not app.exists(): raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    if 'id="a2-premium-settings"' not in s:
        s=s.replace('</head>',CSS+'\n</head>',1)

    # Replace old technical settings with a clean user-facing screen. No storage provider or keys are shown.
    start=s.find('function settings(){')
    end=s.find('\nwindow.savePhotoSettings=',start)
    if start<0: raise SystemExit('settings() not found')
    if end<0:
        end=s.find('\nfunction render(){',start)
    new=r'''function settings(){const role=String(state.profile.role||'').toUpperCase(),name=state.profile.name||'User',email=state.profile.email||auth.currentUser?.email||'—';return`<div class="card settings-hero" style="margin-top:14px"><div class=settings-logo><img src="./logo.svg" alt="A2 MESS HUB"></div><div><div class=settings-title>A2 MESS HUB</div><div class=settings-tagline>Simple • Smart • Organized</div><div class=settings-meta><div><b>Signed in as</b><span>${esc(name)}</span></div><div><b>Role</b><span>${esc(role)}</span></div><div><b>Cloud Sync</b><span>● Connected</span></div></div></div></div><div class=settings-list><div class=settings-item><div class=settings-icon>👤</div><div><strong>Account</strong><small>${esc(email)} · ${esc(role)}</small></div><div class=settings-arrow>›</div></div><div class=settings-item><div class=settings-icon>🔔</div><div><strong>Notifications</strong><small>Meal skip and app alerts</small></div><div class=settings-arrow>›</div></div><div class=settings-item><div class=settings-icon>🛡️</div><div><strong>Security</strong><small>Role-based access and cloud authentication</small></div><div class=settings-arrow>›</div></div><div class=settings-item><div class=settings-icon>ℹ️</div><div><strong>About</strong><small>A2 MESS HUB · Eat • Track • Manage • Sync</small></div><div class=settings-arrow>›</div></div></div><div class="card settings-brand"><div class=crown>👑</div><h3>A2 MESS HUB</h3><div class=settings-note>Built for better mess management</div><p class=powered>⚡ POWERED BY TECHMANZ</p></div>`}
'''
    # Remove legacy savePhotoSettings handler together with old settings block.
    render_pos=s.find('\nfunction render(){',start)
    if render_pos<0: raise SystemExit('render() not found')
    s=s[:start]+new+s[render_pos:]

    # Mobile nav: add compact icons while preserving every existing page and horizontal access.
    old='${n.map(x=>`<button class="${state.page===x?\'on\':\'\'}" onclick="go(\'${x}\')">${label[x]}</button>`).join(\'\')}'
    # Safer direct replacement of the bottom nav expression only.
    bottom_old='<nav class=bottom>${n.map(x=>`<button class="${state.page===x?\'on\':\'\'}" onclick="go(\'${x}\')">${label[x]}</button>`).join(\'\')}</nav>'
    bottom_new='<nav class=bottom>${n.map(x=>`<button class="${state.page===x?\'on\':\'\'}" onclick="go(\'${x}\')"><span class=navico>${({dashboard:\'⌂\',users:\'♟\',members:\'👥\',meals:\'♨\',skipmeal:\'⊘\',inventory:\'▣\',expenses:\'◫\',payments:\'◈\',gas:\'🔥\',closing:\'✓\',reports:\'▥\',backup:\'↥\',settings:\'⚙\'})[x]||\'•\'}</span><span class=navtxt>${label[x]}</span></button>`).join(\'\')}</nav>'
    if bottom_old in s: s=s.replace(bottom_old,bottom_new,1)

    required=['id="a2-premium-settings"','settings-hero','Simple • Smart • Organized','Cloud Sync','Role-based access and cloud authentication','Built for better mess management','class=navico']
    missing=[x for x in required if x not in s]
    if missing: raise SystemExit('Premium settings patch missing: '+', '.join(missing))
    app.write_text(s)
    print('Applied premium settings and navigation UI to',app)
