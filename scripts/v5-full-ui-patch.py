from pathlib import Path
import sys,re

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]: paths=[Path('www/app.html')]

CSS=r'''
<style id="a2-v5-ui">
:root{--v5bg:#02110c;--v5panel:#0a2119;--v5panel2:#0d2b21;--v5line:#1f5c45;--v5text:#f7fff9;--v5muted:#9bb6ab;--v5green:#23e28d;--v5green2:#0fb872;--v5gold:#f7c84b;--v5red:#ff655f;--v5amber:#ffbd45;--v5blue:#52b7ff}
body{background:radial-gradient(circle at 20% -5%,#0f4a35 0,#052016 34%,#010906 100%)!important;color:var(--v5text)!important}
.main{max-width:1180px!important;padding:22px 18px 110px!important}.main>.top{margin-bottom:12px!important}.main>.top h2{font-size:34px!important;font-weight:900!important;letter-spacing:-.035em!important}.main>.top .small{font-size:13px!important;color:#9db7ac!important}
.card,.panel{background:linear-gradient(180deg,rgba(9,35,26,.97),rgba(4,22,16,.98))!important;border:1px solid rgba(62,207,143,.2)!important;border-radius:18px!important;box-shadow:0 14px 42px rgba(0,0,0,.24)!important}.card{padding:17px!important}.grid{gap:12px!important}.metric{font-size:28px!important}.row{background:linear-gradient(180deg,rgba(13,43,32,.78),rgba(6,29,21,.82))!important;border:1px solid rgba(73,211,151,.13)!important;border-radius:14px!important;padding:13px!important}.btn{background:linear-gradient(135deg,#2ce497,#0eba75)!important;color:#022115!important;border:0!important;border-radius:11px!important;font-weight:850!important;box-shadow:0 7px 18px rgba(35,226,141,.18)!important}.ghost{background:rgba(255,255,255,.035)!important;border:1px solid rgba(119,213,171,.14)!important;border-radius:11px!important}.tag{border-radius:8px!important;font-size:10px!important;letter-spacing:.03em!important}.tag.paid{background:#2be292!important}.tag.partial{background:#ffc54f!important}.tag.due{background:#ff635f!important}.note{background:rgba(247,200,75,.07)!important;border:1px solid rgba(247,200,75,.18)!important;color:#f6dfa3!important}
/* APP SHELL */
.a2-shell-brand{display:flex;gap:10px;align-items:center}.a2-shell-logo{width:42px;height:42px;border-radius:12px;border:1px solid rgba(247,200,75,.25);background:#061b14;display:grid;place-items:center;overflow:hidden}.a2-shell-logo img{width:36px;height:36px;object-fit:contain}.a2-shell-title{font-size:19px;font-weight:900;letter-spacing:-.02em}.a2-shell-sub{font-size:10px;color:#b8cfc5;margin-top:2px}.side{background:linear-gradient(180deg,#03150f,#020b08)!important}.side .brand{display:none}.side>.small{display:none}.a2-sidebrand{margin-bottom:18px;padding:6px}.nav button{display:flex!important;align-items:center;gap:10px!important;font-size:13px!important}.nav button .ico{width:22px;text-align:center;font-size:15px}.nav button.on{background:linear-gradient(90deg,rgba(35,226,141,.16),rgba(35,226,141,.04))!important;color:#61f3b2!important}
/* MOBILE FIVE TAB NAV */
.bottom{left:10px!important;right:10px!important;bottom:8px!important;height:68px!important;border-radius:18px!important;padding:5px!important;display:flex!important;justify-content:space-around!important;overflow:hidden!important;background:rgba(3,25,18,.96)!important;border:1px solid rgba(61,209,145,.24)!important;box-shadow:0 10px 35px #0009!important}.bottom button{min-width:0!important;flex:1 1 20%!important;height:56px!important;border-radius:13px!important;display:grid!important;place-items:center!important;align-content:center!important;gap:1px!important;color:#a9c4b8!important}.bottom button.on{background:linear-gradient(180deg,rgba(22,171,106,.32),rgba(7,83,54,.18))!important;color:#45edaa!important}.bottom .navico{font-size:19px!important}.bottom .navtxt{font-size:9px!important;font-weight:700!important}
/* PAGE TITLES / ACTION AREAS */
.page-dashboard .note:first-child,.page-payments .note:first-child{border-radius:14px!important}.page-dashboard .grid>.card,.page-payments .grid>.card,.page-reports .grid>.card{position:relative;overflow:hidden}.page-dashboard .grid>.card:after,.page-reports .grid>.card:after{content:'';position:absolute;width:52px;height:52px;border-radius:50%;right:-18px;top:-18px;background:rgba(35,226,141,.07)}
/* MEMBERS / USERS */
.page-members .card.list,.page-users .card.list{display:grid!important;gap:9px!important}.page-members .row,.page-users .row{min-height:74px!important}.page-members .row>span:first-child b,.page-users .row>span:first-child b{font-size:15px}.page-members .row>span:first-child:before,.page-users .row>span:first-child:before{content:'👤';display:inline-grid;place-items:center;width:32px;height:32px;border-radius:50%;background:rgba(35,226,141,.12);margin-right:8px}
/* MEALS */
.page-meals .list{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:12px!important}.page-meals .list>.row{min-height:150px!important;display:grid!important;grid-template-columns:1fr auto!important;align-content:start!important;padding:16px!important}.page-meals .list>.row:nth-child(3n+1){border-color:rgba(247,200,75,.26)!important}.page-meals .list>.row:nth-child(3n+2){border-color:rgba(82,183,255,.24)!important}.page-meals .list>.row:nth-child(3n+3){border-color:rgba(255,189,69,.24)!important}.page-meals .list>.row>span:first-child b{font-size:18px}.page-meals .list>.row>span:first-child small{display:block!important;margin-top:8px!important;font-size:12px!important}.page-meals .list>.row>span:nth-child(2){font-size:11px!important;color:var(--v5gold)!important}.page-meals .list>.row>span:last-child{grid-column:1/-1!important;margin-top:12px!important}
/* SKIP MEAL */
.page-skipmeal .grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.page-skipmeal .grid>.card{min-height:175px!important;border-color:rgba(73,211,151,.18)!important}.page-skipmeal .grid>.card b{font-size:18px!important}.page-skipmeal .metric{font-size:38px!important;color:#49efad!important}.page-skipmeal .btn{width:100%!important}
/* INVENTORY */
.page-inventory .row{grid-template-columns:1.6fr 1fr .7fr auto!important}.page-inventory .row>span:first-child:before{content:'▣';display:inline-grid;place-items:center;width:30px;height:30px;border-radius:9px;background:rgba(35,226,141,.1);margin-right:8px;color:#47eaaa}.page-inventory .tag.due{background:#f4a62a!important}
/* EXPENSES */
.page-expenses .form{gap:10px!important}.page-expenses .card.list{margin-top:10px!important}.page-expenses .row{grid-template-columns:1.7fr .8fr .8fr auto!important}.page-expenses .row>span:nth-child(2){font-weight:800;color:#fff}.page-expenses .billimg{width:64px!important;height:64px!important;border-radius:10px!important}.page-expenses .billlink{color:#59efad!important}
/* PAYMENTS */
.page-payments .card h3,.page-reports .card h3,.page-closing .card h3{font-size:17px!important}.page-payments .row>span:nth-child(2){font-weight:800}.page-payments .tag{font-weight:800!important}
/* REPORTS */
.page-reports .grid>.card:nth-child(1){border-color:rgba(35,226,141,.25)!important}.page-reports .grid>.card:nth-child(2){border-color:rgba(255,99,95,.2)!important}.page-reports .grid>.card:nth-child(3){border-color:rgba(82,183,255,.22)!important}
/* GAS */
.page-gas .card{border-color:rgba(82,183,255,.18)!important}.page-gas .btn{background:linear-gradient(135deg,#36b8ff,#1673ce)!important;color:white!important}
/* BACKUP */
.page-backup .card{border-color:rgba(52,220,157,.2)!important}
/* SETTINGS */
.page-settings .settings-hero{border-color:rgba(35,226,141,.23)!important}.page-settings .settings-item{min-height:78px!important}.page-settings .settings-icon{background:rgba(35,226,141,.12)!important}.page-settings .settings-brand{border-color:rgba(247,200,75,.18)!important}
/* MORE PAGE */
.v5-more-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.v5-more-item{min-height:105px;padding:16px;border-radius:16px;background:linear-gradient(180deg,rgba(12,45,33,.93),rgba(6,26,19,.95));border:1px solid rgba(64,209,145,.15);display:grid;grid-template-columns:42px 1fr;gap:12px;align-items:center;cursor:pointer}.v5-more-icon{width:42px;height:42px;border-radius:12px;background:rgba(35,226,141,.12);display:grid;place-items:center;font-size:20px}.v5-more-item b{font-size:15px}.v5-more-item small{display:block;color:var(--v5muted);margin-top:4px;font-size:11px}
@media(max-width:900px){.main{padding:16px 10px 92px!important}.main>.top h2{font-size:28px!important}.page-meals .list{grid-template-columns:1fr 1fr!important}.v5-more-grid{grid-template-columns:1fr 1fr!important}}
@media(max-width:620px){.page-meals .list,.page-skipmeal .grid{grid-template-columns:1fr!important}.page-expenses .row,.page-inventory .row,.page-members .row,.page-users .row,.page-payments .row{grid-template-columns:1fr auto!important}.page-expenses .row>span:nth-child(3),.page-inventory .row>span:nth-child(3),.page-payments .row>span:nth-child(3){grid-column:1/2}.v5-more-grid{grid-template-columns:1fr 1fr!important}.main>.top h2{font-size:27px!important}.card{border-radius:16px!important}.settings-meta{grid-template-columns:1fr 1fr!important}}
</style>
'''

for app in paths:
    if not app.exists(): raise SystemExit(f'App file not found: {app}')
    s=app.read_text()
    if 'id="a2-v5-ui"' not in s: s=s.replace('</head>',CSS+'\n</head>',1)

    # Add page icons, subtitles and compact role-aware More screen.
    anchor='window.go=p=>{state.page=p;render()};'
    helpers=r'''const v5Icon={dashboard:'⌂',users:'♟',members:'👥',meals:'♨',skipmeal:'⊘',inventory:'▣',expenses:'◫',payments:'◈',gas:'🔥',closing:'✓',reports:'▥',backup:'↥',settings:'⚙',more:'•••'};
const v5Subtitle={dashboard:'Simple • Smart • Organized',users:'Manage app access and roles',members:'Plans, balances and member status',meals:'Breakfast • Lunch • Dinner',skipmeal:'Reduce cooking quantity before cutoff',inventory:'Track shared stock and low items',expenses:'Search, filter and control mess spending',payments:'Monthly collection and member balances',gas:'LPG order access',closing:'Close month and carry balance forward',reports:'Monthly overview and settlement',backup:'Protect monthly mess records',settings:'Manage your account & app preferences',more:'All management tools'};
function morePage(){const prim=new Set(['dashboard','meals','expenses','reports','more']),items=nav().filter(x=>!prim.has(x));return`<div class=v5-more-grid>${items.map(x=>`<div class=v5-more-item onclick="go('${x}')"><div class=v5-more-icon>${v5Icon[x]||'•'}</div><div><b>${label[x]}</b><small>${v5Subtitle[x]||'Open section'}</small></div></div>`).join('')}</div>`}
'''
    if 'function morePage(){' not in s and anchor in s: s=s.replace(anchor,anchor+'\n'+helpers,1)

    # Upgrade labels with More if missing.
    s=s.replace("settings:'Settings'};","settings:'Settings',more:'More'};",1)

    # Replace shell layout. Keeps desktop sidebar all pages, mobile only 5 tabs.
    a=s.find('function layout(body){')
    b=s.find('\nwindow.go=',a)
    if a<0 or b<0: raise SystemExit('layout markers not found')
    layout=r'''function layout(body){const n=nav(),mobile=['dashboard','meals','expenses','reports','more'];const mobileActive=mobile.includes(state.page)?state.page:'more';appEl.innerHTML=`<div class=app><aside class=side><div class=a2-sidebrand><div class=a2-shell-brand><div class=a2-shell-logo><img src="./logo.svg" alt="A2"></div><div><div class=a2-shell-title>A2 MESS HUB</div><div class=a2-shell-sub>Eat • Track • Manage</div></div></div></div><div class=nav>${n.map(x=>`<button class="${state.page===x?'on':''}" onclick="go('${x}')"><span class=ico>${v5Icon[x]||'•'}</span><span>${label[x]}</span></button>`).join('')}</div><p class=powered style="margin-top:26px">⚡ TECHMANZ</p></aside><main class="main page-${state.page}"><div class=top><div><h2 style="margin:0">${state.page==='more'?'More':label[state.page]}</h2><div class=small>${v5Subtitle[state.page]||'Realtime cloud sync'}</div></div><button class=ghost onclick=logout()>Logout</button></div>${body}</main></div><nav class=bottom>${mobile.map(x=>`<button class="${mobileActive===x?'on':''}" onclick="go('${x}')"><span class=navico>${v5Icon[x]}</span><span class=navtxt>${label[x]}</span></button>`).join('')}</nav>`}'''
    s=s[:a]+layout+s[b:]

    # Add More to render map without altering business logic.
    s=s.replace('backup:backupPage,settings}', 'backup:backupPage,settings,more:morePage}',1)
    s=s.replace('reports,backup:backupPage,settings}', 'reports,backup:backupPage,settings,more:morePage}',1)
    s=s.replace('reports,settings}', 'reports,settings,more:morePage}',1)

    # If generic render map shape differs, patch just before closing map.
    if 'more:morePage' not in s[s.find('function render(){'):s.find('onAuthStateChanged',s.find('function render(){'))]:
        rp=s.find('function render(){')
        re=s.find('}catch(e)',rp)
        frag=s[rp:re]
        frag=frag.replace('settings}[state.page]','settings,more:morePage}[state.page]')
        s=s[:rp]+frag+s[re:]

    # Friendlier copy on major pages to match approved model UI.
    s=s.replace('Subscription members · ${month}','Members · ${month}')
    s=s.replace('Monthly payment control · ${month}','Payments · ${month}')
    s=s.replace('Payment Transactions','Payment History')
    s=s.replace('Live menu','Today’s Meals')

    required=['id="a2-v5-ui"','function morePage(){','v5-more-grid','Simple • Smart • Organized','mobile=[\'dashboard\',\'meals\',\'expenses\',\'reports\',\'more\']','a2-shell-logo','page-${state.page}']
    missing=[x for x in required if x not in s]
    if missing: raise SystemExit('V5 UI patch missing: '+', '.join(missing))
    app.write_text(s)
    print('Applied A2 MESS HUB V5 full UI to',app)
