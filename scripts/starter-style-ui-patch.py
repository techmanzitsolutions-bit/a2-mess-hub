from pathlib import Path
import re, sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

CSS=r'''<style id="a2-starter-green-ui">
:root{
 --a2-green:#0a9b68;--a2-green2:#087b55;--a2-deep:#075c43;--a2-ink:#17352c;--a2-muted:#71867f;
 --a2-bg:#f4f8f6;--a2-card:#fff;--a2-line:#e3ece8;--a2-soft:#eaf8f2;--a2-danger:#d95663;
 --a2-shadow:0 12px 34px rgba(24,66,52,.08);--a2-shadow-lg:0 22px 70px rgba(20,70,52,.13);
 --v5bg:#f4f8f6;--v5panel:#fff;--v5panel2:#fcfefd;--v5line:#e3ece8;--v5text:#17352c;--v5muted:#71867f;
 --v5green:#0a9b68;--v5green2:#087b55;--v5gold:#c59228;--v5red:#d95663;--v5amber:#bd7b21;--v5blue:#2d78a8;
}
html{background:var(--a2-bg)!important}body{background:var(--a2-bg)!important;color:var(--a2-ink)!important;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif!important}
/* login */
.center{background:radial-gradient(circle at 88% 4%,rgba(10,155,104,.13),transparent 32%),radial-gradient(circle at 4% 96%,rgba(10,155,104,.08),transparent 28%),var(--a2-bg)!important;padding:24px!important}
.panel{width:min(430px,100%)!important;background:#fff!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important;border-radius:24px!important;box-shadow:var(--a2-shadow-lg)!important;padding:30px!important}
.a2-logo-stage{width:66px!important;height:66px!important;margin:0 auto 14px!important;border-radius:20px!important;background:linear-gradient(145deg,var(--a2-green),var(--a2-green2))!important;display:grid!important;place-items:center!important;filter:none!important;box-shadow:0 10px 24px rgba(10,155,104,.22)!important}
.a2-logo-stage img{display:none!important}.a2-logo-stage:before{content:'A2';color:#fff;font-size:26px;font-weight:950}.a2-logo-stage:after{display:none!important}
.a2-brand-name{color:var(--a2-ink)!important;font-size:24px!important;letter-spacing:.04em!important;margin:0!important}.a2-brand-name span{color:var(--a2-green)!important}.a2-brand-tag,.sub{color:var(--a2-muted)!important}.a2-powered{color:var(--a2-green2)!important;font-weight:800!important}
.field label{color:var(--a2-muted)!important;font-weight:700!important}.field input,.field select,.field textarea{background:#fbfdfc!important;color:var(--a2-ink)!important;border:1px solid #d9e7e1!important;border-radius:12px!important;padding:12px 13px!important;outline:none!important}.field input:focus,.field select:focus,.field textarea:focus{border-color:#68c5a5!important;box-shadow:0 0 0 3px #e6f7f1!important;background:#fff!important}
/* shell */
.app{background:var(--a2-bg)!important;grid-template-columns:250px minmax(0,1fr)!important}.side{background:linear-gradient(180deg,#0c8f63,#087b55 58%,#066547)!important;border-right:0!important;padding:22px 17px!important;box-shadow:8px 0 30px rgba(10,83,59,.08)!important}
.a2-sidebrand{margin:0 0 20px!important;padding:2px 7px!important}.a2-shell-brand{gap:11px!important}.a2-shell-logo{width:42px!important;height:42px!important;border:0!important;border-radius:13px!important;background:#fff!important;box-shadow:0 8px 20px rgba(3,63,43,.16)!important}.a2-shell-logo img{display:none!important}.a2-shell-logo:before{content:'A2';color:var(--a2-green);font-size:18px;font-weight:950}.a2-shell-title{color:#fff!important;font-size:17px!important;font-weight:850!important}.a2-shell-sub{color:#caeee1!important;font-size:10px!important}
.nav{gap:6px!important;margin-top:8px!important}.nav button{min-height:44px!important;padding:10px 12px!important;border:0!important;border-radius:12px!important;background:transparent!important;color:#d9f3ea!important;font-size:13px!important;font-weight:700!important}.nav button:hover{background:rgba(255,255,255,.10)!important;color:#fff!important}.nav button.on{background:rgba(255,255,255,.17)!important;color:#fff!important;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08)!important}.nav button .ico{color:inherit!important}
.side .powered{width:104px!important;height:78px!important;min-height:78px!important;margin:22px auto 0!important;border-color:rgba(255,255,255,.18)!important;background-color:rgba(255,255,255,.08)!important;box-shadow:none!important}
.main{max-width:none!important;width:100%!important;padding:27px 32px 36px!important;background:var(--a2-bg)!important;color:var(--a2-ink)!important}.main>.top{min-height:54px!important;margin-bottom:20px!important}.main>.top h2{font-size:27px!important;font-weight:850!important;letter-spacing:-.02em!important;color:var(--a2-ink)!important}.main>.top .small,.small,.muted{color:var(--a2-muted)!important}.main>.top>.ghost{background:#fff!important;border:1px solid var(--a2-line)!important;color:var(--a2-ink)!important;box-shadow:0 5px 18px rgba(24,66,52,.05)!important}
/* shared surfaces */
.card,.panel{background:#fff!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important;box-shadow:var(--a2-shadow)!important}.card{border-radius:18px!important;padding:19px!important}.row{background:#fcfefd!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important;border-radius:12px!important;padding:12px 13px!important}.row b,.row strong{color:var(--a2-ink)!important}.page-expenses .row>span:nth-child(2),.page-payments .row>span:nth-child(2){color:var(--a2-ink)!important}.metric{color:var(--a2-ink)!important;font-size:25px!important;font-weight:850!important}.grid{gap:16px!important}.grid>.card{position:relative!important;overflow:hidden!important;min-height:118px!important}.grid>.card:after{background:var(--a2-soft)!important;opacity:1!important}
.btn{background:linear-gradient(135deg,var(--a2-green),var(--a2-green2))!important;color:#fff!important;border:0!important;border-radius:11px!important;font-weight:800!important;box-shadow:0 8px 18px rgba(10,155,104,.16)!important}.ghost{background:#fff!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important;border-radius:11px!important;font-weight:700!important}.ghost:hover{background:var(--a2-soft)!important;color:var(--a2-green2)!important;border-color:#bfe4d6!important}.ghost.danger,.danger{background:#fff!important;color:var(--a2-danger)!important;border-color:#f1c9ce!important}
.tag{background:var(--a2-soft)!important;color:var(--a2-green2)!important;border-radius:999px!important}.tag.paid{background:#e6f7ef!important;color:#087b55!important}.tag.partial{background:#fff7dc!important;color:#a06b0e!important}.tag.due{background:#fff0f1!important;color:#c94c59!important}.note{background:#fffaf0!important;border:1px solid #f0dfb1!important;color:#75602e!important}.ok{background:var(--a2-soft)!important;border-color:#cce9de!important;color:var(--a2-green2)!important}
/* dashboard V6 */
.v6-hero{padding:20px!important;background:linear-gradient(135deg,#0b9c6a,#087b55)!important;color:#fff!important;border:0!important;border-radius:18px!important;box-shadow:0 14px 30px rgba(10,126,87,.18)!important}.v6-hero .small{color:#d9f3ea!important}.v6-hero h3{color:#fff!important}.v6-hero .tag{background:rgba(255,255,255,.16)!important;color:#fff!important;border:1px solid rgba(255,255,255,.14)!important}
.v6-kpis{gap:16px!important;margin-top:16px!important}.v6-kpi{position:relative!important;padding:18px!important;border-radius:18px!important;background:#fff!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important;box-shadow:var(--a2-shadow)!important}.v6-kpi small{color:var(--a2-muted)!important}.v6-kpi b{color:var(--a2-ink)!important;font-size:24px!important}.v6-kpi.blue b{color:#2d78a8!important}.v6-kpi.red b{color:#c94c59!important}
.v6-strip{background:#fff!important;border:1px solid var(--a2-line)!important}.v6-strip b{color:var(--a2-ink)!important}.v6-meal{background:#f8fbfa!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important}.v6-meal b,.v6-meal strong{color:var(--a2-ink)!important}.v6-alert{background:#fff!important}.v6-alert.danger{border-color:#f0c0c5!important}.v6-alert.warn{border-color:#eedaa7!important}.v6-progress{background:#e7efec!important}.v6-progress i{background:linear-gradient(90deg,var(--a2-green),#48c79d)!important}.v6-quick button{min-height:64px!important}
/* feature pages */
.page-members .row>span:first-child:before,.page-users .row>span:first-child:before,.page-inventory .row>span:first-child:before{background:var(--a2-soft)!important;color:var(--a2-green)!important}.page-meals .list>.row{background:#fff!important;border-color:var(--a2-line)!important}.page-meals .list>.row:nth-child(3n+1),.page-meals .list>.row:nth-child(3n+2),.page-meals .list>.row:nth-child(3n+3){border-color:var(--a2-line)!important}.page-meals .list>.row>span:nth-child(2){color:var(--a2-green2)!important}.page-skipmeal .grid>.card,.page-inventory .row,.page-gas .card,.page-backup .card{border-color:var(--a2-line)!important}.page-skipmeal .metric{color:var(--a2-green)!important}.page-gas .btn{background:linear-gradient(135deg,#329ac8,#2877a1)!important;color:#fff!important}
.v5-more-grid{gap:12px!important}.v5-more-item{background:#fff!important;color:var(--a2-ink)!important;border:1px solid var(--a2-line)!important;box-shadow:var(--a2-shadow)!important}.v5-more-icon{background:var(--a2-soft)!important;color:var(--a2-green2)!important}.v5-more-item small{color:var(--a2-muted)!important}
.settings-hero,.settings-card,.settings-item,.settings-brand{background:#fff!important;color:var(--a2-ink)!important;border-color:var(--a2-line)!important}.settings-icon{background:var(--a2-soft)!important;color:var(--a2-green2)!important}.settings-meta,.settings-sub,.settings-note{color:var(--a2-muted)!important}
/* expense table and media */
.expense-wrap{background:#fff!important}.expense-table th{color:var(--a2-muted)!important}.expense-table td{background:#fcfefd!important;color:var(--a2-ink)!important;border-color:var(--a2-line)!important}.expense-mobile-label,.readonly-note{color:var(--a2-muted)!important}.billpreview{background:#f8fbfa!important;border-color:#b8d9cc!important}.billpreview img,.billimg,.expense-photo{background:#f0f6f3!important;border-color:var(--a2-line)!important}.billlink{color:var(--a2-green2)!important}
/* modal / toast */
.modal{background:rgba(12,36,29,.44)!important;backdrop-filter:blur(7px)!important}.modal>.card{box-shadow:0 28px 80px rgba(13,48,37,.22)!important}.toast{background:#0c7f59!important;color:#fff!important;border-color:#b9dfd1!important;box-shadow:0 12px 35px rgba(13,85,62,.24)!important}
/* bottom nav */
.bottom{left:0!important;right:0!important;bottom:0!important;height:auto!important;min-height:70px!important;border-radius:0!important;padding:8px 7px max(8px,env(safe-area-inset-bottom))!important;background:rgba(255,255,255,.97)!important;border:0!important;border-top:1px solid var(--a2-line)!important;box-shadow:0 -8px 30px rgba(24,66,52,.08)!important;backdrop-filter:blur(14px)!important}.bottom button{height:52px!important;border-radius:11px!important;color:#82958e!important}.bottom button.on{background:var(--a2-soft)!important;color:var(--a2-green2)!important}.bottom .navico{font-size:18px!important}.bottom .navtxt{font-size:10px!important}
.powered{border-color:#d9e7e1!important;box-shadow:0 8px 22px rgba(13,52,40,.10)!important}
@media(max-width:1100px){.v6-kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important}.v6-kpis>.v6-kpi:last-child{grid-column:auto}}
@media(max-width:900px){.main{padding:20px 15px calc(88px + env(safe-area-inset-bottom))!important}.main>.top h2{font-size:24px!important}.v6-kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important}.v6-quick{grid-template-columns:repeat(2,minmax(0,1fr))!important}.v5-more-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@media(max-width:680px){.card{padding:15px!important;border-radius:16px!important}.panel{padding:24px 20px!important}.v6-kpis{grid-template-columns:1fr!important}.v6-strip{grid-template-columns:repeat(4,1fr)!important}.v6-strip>div:first-child{grid-column:1/-1!important}.v6-alerts{grid-template-columns:1fr 1fr!important}.v6-meals{grid-template-columns:repeat(3,1fr)!important}.v6-meal{padding:11px!important}.v6-meal strong{font-size:20px!important}.page-meals .list{grid-template-columns:1fr!important}}
@media(max-width:560px){.center{padding:16px!important}.panel{padding:23px 18px!important}.main{padding-left:10px!important;padding-right:10px!important}.main>.top h2{font-size:23px!important}.v6-hero h3{font-size:23px!important}.v6-alerts{grid-template-columns:1fr!important}.v6-quick{grid-template-columns:1fr 1fr!important}.v5-more-grid{grid-template-columns:1fr 1fr!important}.settings-meta{grid-template-columns:1fr 1fr!important}}
@media(max-width:380px){.v6-quick,.v5-more-grid{grid-template-columns:1fr!important}}
</style>'''

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    s=re.sub(r'\n?<style id="a2-starter-green-ui">.*?</style>\n?', '\n', s, flags=re.S)
    s=s.replace('</head>',CSS+'\n</head>',1)
    s=s.replace('<meta name="theme-color" content="#071711">','<meta name="theme-color" content="#0a9b68">')
    s=s.replace('<meta name="theme-color" content="#07130f">','<meta name="theme-color" content="#0a9b68">')
    app.write_text(s)
    print('Applied A2 starter green UI to',app)

# Keep installed-PWA chrome aligned with the green/white UI.
base=paths[0].parent
manifest=base/'manifest.webmanifest'
if manifest.exists():
    m=manifest.read_text()
    m=m.replace('"background_color":"#07130f"','"background_color":"#f4f8f6"')
    m=m.replace('"theme_color":"#07130f"','"theme_color":"#0a9b68"')
    m=m.replace('"background_color": "#07130f"','"background_color": "#f4f8f6"')
    m=m.replace('"theme_color": "#07130f"','"theme_color": "#0a9b68"')
    manifest.write_text(m)
