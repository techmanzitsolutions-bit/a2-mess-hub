from pathlib import Path
import re

app=Path('/tmp/a2-pwa/www/app.html')
if not app.exists():
    app=Path('www/app.html')
s=app.read_text()

# Force Skip Meal into every role nav array that contains Meals.
m=re.search(r"const nav=\(\)=>.*?;",s)
if not m:
    raise SystemExit('nav function not found')
nav=m.group(0)
def fix_array(match):
    arr=match.group(0)
    if "'meals'" in arr and "'skipmeal'" not in arr:
        arr=arr.replace("'meals'","'meals','skipmeal'",1)
    return arr
fixed=re.sub(r"\[[^\]]*\]",fix_array,nav)
s=s[:m.start()]+fixed+s[m.end():]

# Add an unmistakable member quick-action next to Logout.
marker='<button class=ghost onclick=logout()>Logout</button>'
quick="${state.profile.role==='member'?`<button class=btn onclick=\"go('skipmeal')\">🍽️ Skip Meal / No Need</button>`:''}"+marker
if 'MEAL SKIP QUICK ACTION' not in s:
    if marker not in s:
        raise SystemExit('layout logout marker not found')
    s=s.replace(marker,'<!-- MEAL SKIP QUICK ACTION -->'+quick,1)

# Confirm the page renderer and label are present too.
required=["'skipmeal'","skipmeal:'Skip Meal'",'skipmeal:mealSkipPage','MEAL SKIP QUICK ACTION']
missing=[x for x in required if x not in s]
if missing:
    raise SystemExit('Member skip visibility fix missing: '+', '.join(missing))

app.write_text(s)
print('Forced Skip Meal nav + member quick action visibility')
