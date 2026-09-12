from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

PRO_CSS=r'''
<style id="a2-pro-ui">
:root{--bg:#06110d;--panel:#0b1d17;--panel2:#10271f;--line:#214238;--text:#f4fbf7;--muted:#9fb8ae;--green:#4de3a1;--green2:#1ab87a;--gold:#f2c764;--danger:#ff7e88;--shadow:0 18px 55px rgba(0,0,0,.28)}
html{background:var(--bg)}body{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif!important;letter-spacing:-.01em;background:radial-gradient(circle at 18% -8%,#173f31 0,#071510 38%,#030907 100%)!important;color:var(--text)!important}
.main{width:100%;max-width:1440px;margin:0 auto;padding:28px 30px 96px!important}.top{gap:16px}.top h2{font-size:30px!important;line-height:1.1;letter-spacing:-.035em}.small,.muted{color:var(--muted)!important}.small{line-height:1.45}.card,.panel{background:linear-gradient(180deg,rgba(15,40,31,.96),rgba(7,24,18,.98))!important;border:1px solid rgba(132,226,184,.14)!important;border-radius:18px!important;box-shadow:var(--shadow)!important}.card{padding:18px!important}.metric{font-size:30px!important;letter-spacing:-.04em}.brand{font-size:23px!important;letter-spacing:-.02em}.side{width:260px!important;padding:22px 16px!important;background:linear-gradient(180deg,#051610f5,#03100cf8)!important;border-right:1px solid rgba(132,226,184,.10)!important}.app{grid-template-columns:260px 1fr!important}.nav{gap:5px!important}.nav button{border:0!important;background:transparent!important;border-radius:12px!important;padding:12px 13px!important;color:#aec6bc!important;font-weight:650!important;transition:.18s ease}.nav button:hover{background:rgba(255,255,255,.055)!important;color:#fff!important}.nav button.on{background:linear-gradient(135deg,rgba(77,227,161,.18),rgba(242,199,100,.08))!important;color:#74f0b5!important;box-shadow:inset 0 0 0 1px rgba(77,227,161,.14)}
.btn,.ghost{min-height:42px!important;border-radius:11px!important;font-weight:750!important;transition:transform .15s ease,filter .15s ease}.btn{background:linear-gradient(135deg,var(--green),var(--green2))!important;box-shadow:0 8px 22px rgba(26,184,122,.18)}.btn:active,.ghost:active{transform:scale(.98)}.ghost{background:rgba(255,255,255,.045)!important;border:1px solid rgba(255,255,255,.10)!important}.danger{color:#ffb3ba!important;border-color:rgba(255,126,136,.28)!important}
.field label{font-size:11px!important;letter-spacing:.06em;text-transform:uppercase;font-weight:750;color:#96b4a8!important}.field input,.field select,.field textarea{min-height:44px!important;border-radius:11px!important;background:#04120e!important;border:1px solid rgba(126,220,177,.16)!important;padding:11px 12px!important;outline:none}.field input:focus,.field select:focus,.field textarea:focus{border-color:rgba(77,227,161,.55)!important;box-shadow:0 0 0 3px rgba(77,227,161,.08)}
.grid{gap:14px!important}.row{border:1px solid rgba(255,255,255,.055)!important;background:rgba(255,255,255,.026)!important;border-radius:13px!important;padding:13px 14px!important}.tag{background:#64e6ad!important;color:#062117!important}.tag.due{background:#ef7b84!important;color:#fff!important}.note{border-radius:12px!important;background:rgba(242,199,100,.075)!important;border:1px solid rgba(242,199,100,.18)!important;color:#f5dfaa!important}
/* clearer meal workspace */
.page-meals .list{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:12px!important;background:transparent!important;border:0!important;box-shadow:none!important;padding:0!important}.page-meals .list>.row{display:grid!important;grid-template-columns:1fr auto!important;min-height:112px;align-content:center;background:linear-gradient(145deg,rgba(14,44,33,.96),rgba(7,25,19,.96))!important;border:1px solid rgba(77,227,161,.12)!important;box-shadow:0 12px 30px rgba(0,0,0,.16)!important}.page-meals .list>.row>span:first-child{font-size:16px}.page-meals .list>.row>span:nth-child(2){color:var(--gold);font-size:12px;font-weight:750}.page-meals .list>.row>span:nth-child(3){display:none}.page-meals .list>.row>span:last-child{grid-column:1/-1;margin-top:8px}
.page-skipmeal .grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.page-skipmeal .grid>.card{min-height:155px;display:flex;flex-direction:column;justify-content:space-between}.page-skipmeal .grid>.card b{font-size:17px}.page-skipmeal .metric{font-size:38px!important;color:var(--green)}
.page-expenses .card.list,.page-payments .card.list,.page-members .card.list,.page-inventory .card.list{overflow:hidden}.billimg{width:74px!important;height:74px!important;border-radius:10px!important}
.bottom{backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 14px 40px #0008}.bottom button{font-weight:700!important}
@media(max-width:900px){.app{display:block!important}.main{padding:18px 12px 92px!important}.top h2{font-size:25px!important}.page-meals .list,.page-skipmeal .grid{grid-template-columns:1fr 1fr!important}.card{padding:15px!important}}
@media(max-width:620px){.page-meals .list,.page-skipmeal .grid{grid-template-columns:1fr!important}.main>.top{align-items:flex-start}.main>.top>button{min-width:auto}.metric{font-size:26px!important}.row{gap:10px!important}}
</style>
'''

for app in paths:
    if not app.exists(): raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    if 'id="a2-pro-ui"' not in s:
        s=s.replace('</head>',PRO_CSS+'\n</head>',1)

    # page-specific class allows a clean two-column Meal / Skip Meal presentation without touching data logic.
    s=s.replace('<main class=main>', '<main class="main page-${state.page}">')

    # clearer copy, without changing behavior.
    s=s.replace('<p class=muted>Live menu</p>', '<p class=muted>Meal schedule · clear cards for breakfast, lunch and dinner</p>')
    s=s.replace('Tell the kitchen before cooking so food quantity can be reduced.', 'Choose No Need before the kitchen cutoff so cooking quantity updates clearly.')
    s=s.replace('Live member skip count before cooking.', 'Live cooking quantity based on member meal skips.')

    required=['id="a2-pro-ui"','page-${state.page}','page-meals .list','page-skipmeal .grid','Meal schedule · clear cards','Live cooking quantity based on member meal skips.']
    missing=[x for x in required if x not in s]
    if missing: raise SystemExit('Professional UI patch missing: '+', '.join(missing))
    app.write_text(s)
    print(f'Applied professional UI refresh to {app}')
