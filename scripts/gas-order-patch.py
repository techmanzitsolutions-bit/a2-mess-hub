from pathlib import Path

app = Path('/tmp/a2-pwa/www/app.html')
if not app.exists():
    app = Path('www/app.html')
s = app.read_text()

# Add Order Gas to all role navigation menus.
s = s.replace("['dashboard','users','members','meals','inventory','expenses','payments','reports','settings']", "['dashboard','users','members','meals','inventory','expenses','payments','gas','reports','settings']")
s = s.replace("['dashboard','meals','inventory','expenses','settings']", "['dashboard','meals','inventory','expenses','gas','settings']")
s = s.replace("['dashboard','meals','expenses','payments','settings']", "['dashboard','meals','expenses','payments','gas','settings']")
s = s.replace("['dashboard','meals','payments','settings']", "['dashboard','meals','payments','gas','settings']")

# Add page label.
if "gas:'Order Gas'" not in s:
    s = s.replace("reports:'Reports',settings:'Settings'", "gas:'Order Gas',reports:'Reports',settings:'Settings'")

# Add a dedicated LPG order page and launcher.
if 'function gasOrder(){' not in s:
    marker = 'function reports(){'
    if marker not in s:
        raise SystemExit('reports marker not found')
    gas = r'''function gasOrder(){return`<div class="card" style="margin-top:14px"><div class=top><div><h3 style="margin:0">🔥 ADNOC LPG Order</h3><div class=small>Quick access to ADNOC Distribution</div></div><span class=tag>25 lbs</span></div><div style="margin-top:18px;display:grid;gap:12px"><div class=note><b>Usual order:</b> Small LPG cylinder (25 lbs). Tap below to open the installed ADNOC Distribution app directly. Then continue the LPG order inside ADNOC.</div><button class=btn style="padding:15px;font-size:17px" onclick="openAdnocGas()">🔥 OPEN ADNOC APP</button><div class=small>A2 MESS HUB opens ADNOC directly when installed. ADNOC does not expose a supported public deep link to the exact LPG checkout screen, so the final LPG selection and payment confirmation remain inside ADNOC.</div></div></div>`}
window.openAdnocGas=()=>{const ua=navigator.userAgent||'',android=/Android/i.test(ua),ios=/iPhone|iPad|iPod/i.test(ua);if(android){window.location.href='intent:#Intent;action=android.intent.action.MAIN;category=android.intent.category.LAUNCHER;package=ae.gov.adnoc;end';return}if(ios){window.location.href='https://apps.apple.com/ae/app/adnoc-dist/id1015371099';return}window.open('https://www.adnocdistribution.ae/en/lpg-campaign/','_blank','noopener')};
'''
    s = s.replace(marker, gas + marker, 1)

# Include the page in the renderer.
s = s.replace('{dashboard,users,members,meals,inventory,expenses,payments,reports,settings}', '{dashboard,users,members,meals,inventory,expenses,payments,gas:gasOrder,reports,settings}')

required = [
    'function gasOrder(){',
    'window.openAdnocGas=',
    'package=ae.gov.adnoc',
    'action=android.intent.action.MAIN',
    'category=android.intent.category.LAUNCHER',
    "gas:'Order Gas'"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('Gas order patch missing: ' + ', '.join(missing))

app.write_text(s)
print('Added direct installed-app ADNOC LPG launcher')
