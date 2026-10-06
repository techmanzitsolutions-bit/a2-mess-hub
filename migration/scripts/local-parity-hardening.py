from pathlib import Path
import re
import sys

app = Path(sys.argv[1] if len(sys.argv) > 1 else "migration/techmanz-build/app.html")
s = app.read_text()

date_block = r"""function a2Date(v,depth=0){try{if(v===null||v===undefined||depth>5)return null;if(v instanceof Date)return isNaN(v)?null:v;if(typeof v?.toDate==='function')return a2Date(v.toDate(),depth+1);if(typeof v?.toMillis==='function')return a2Date(v.toMillis(),depth+1);if(typeof v==='string'||typeof v==='number'){const d=new Date(v);return d instanceof Date&&!isNaN(d)?d:null}if(typeof v==='object'){if(Object.prototype.hasOwnProperty.call(v,'__a2Timestamp'))return a2Date(v.__a2Timestamp,depth+1);if(v._date)return a2Date(v._date,depth+1);const sec=Number(v.seconds??v._seconds);if(Number.isFinite(sec)){const ns=Number(v.nanoseconds??v._nanoseconds??0),d=new Date(sec*1000+ns/1e6);return isNaN(d)?null:d}for(const k of ['value','date','iso','timestamp'])if(v[k]){const d=a2Date(v[k],depth+1);if(d)return d}}return null}catch{return null}}
function expenseDate(x){const d=a2Date(x?.createdAt)||a2Date(x?.updatedAt);return d?d.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Dubai'}):'Date not recorded'}
function expenseAddedBy(x){return x?.createdByName||((x?.createdBy&&x.createdBy===auth.currentUser?.uid)?state.profile.name:'Admin / Chef')}
function expenseDateKey(x){const t=a2Date(x?.createdAt)||a2Date(x?.updatedAt);return t?t.getTime():0}
function expenseDateLabel(x){const t=a2Date(x?.createdAt)||a2Date(x?.updatedAt);return t?t.toLocaleString('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:true,timeZone:'Asia/Dubai'}):'Date not recorded'}"""

pat = re.compile(
    r"function expenseDate\(x\)\{.*?\}\n"
    r"function expenseAddedBy\(x\)\{.*?\}\n"
    r"function expenseDateKey\(x\)\{.*?\}\n"
    r"function expenseDateLabel\(x\)\{.*?\}\n"
    r"window\.setExpenseView",
    re.S,
)
s, n = pat.subn(date_block + "\nwindow.setExpenseView", s, count=1)
if n != 1:
    raise SystemExit("Expense date block not found")

expense_fn = r"""function expenses(){
 const v=window._expenseView||{},q=String(v.q||'').trim().toLowerCase(),cat=v.cat||'ALL',sort=v.sort||'newest';
 const cats=[...new Set(state.data.expenses.map(x=>String(x.category||'General').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
 let rows=state.data.expenses.filter(x=>(cat==='ALL'||String(x.category||'General')===cat)&&(!q||[x.title,x.category,x.amount,x.createdBy,x.createdByName,expenseDateLabel(x)].some(y=>String(y??'').toLowerCase().includes(q))));
 rows.sort((a,b)=>sort==='oldest'?expenseDateKey(a)-expenseDateKey(b):sort==='amountHigh'?Number(b.amount||0)-Number(a.amount||0):sort==='amountLow'?Number(a.amount||0)-Number(b.amount||0):sort==='name'?String(a.title||'').localeCompare(String(b.title||'')):expenseDateKey(b)-expenseDateKey(a));
 return `<div class=top style="margin-top:14px"><p class=muted>Expenses ordered newest first · search and filter available</p>${state.profile.role==='admin'||state.profile.role==='chef'?'<button class=btn onclick=expenseForm()>+ Expense</button>':''}</div>
 <div class=card style="margin-bottom:12px"><div class=form>
   <div class=field><label>Search</label><input value="${esc(v.q||'')}" placeholder="Search expense, category, amount or date…" oninput="setExpenseView('q',this.value)"></div>
   <div class=field><label>Category</label><select onchange="setExpenseView('cat',this.value)"><option value=ALL>All Categories</option>${cats.map(c=>`<option value="${esc(c)}" ${cat===c?'selected':''}>${esc(c)}</option>`).join('')}</select></div>
   <div class=field><label>Sort By</label><select onchange="setExpenseView('sort',this.value)"><option value=newest ${sort==='newest'?'selected':''}>Newest First</option><option value=oldest ${sort==='oldest'?'selected':''}>Oldest First</option><option value=amountHigh ${sort==='amountHigh'?'selected':''}>Amount: High → Low</option><option value=amountLow ${sort==='amountLow'?'selected':''}>Amount: Low → High</option><option value=name ${sort==='name'?'selected':''}>Name A → Z</option></select></div>
   <div class=field><label>Results</label><div class=note>${rows.length} expense(s) · AED ${rows.reduce((a,x)=>a+Number(x.amount||0),0).toFixed(2)}</div></div>
 </div></div>
 <div class="card expense-table">
   <div class="expense-head"><b>Expense</b><b>Added Date</b><b>Amount</b><b>Category / Method</b><b>Added By / Actions</b></div>
   <div class=list>${rows.map(x=>`<div class="row expense-row">
     <span><b>${esc(x.title)}</b>${x.billUrl?`<br><button class="ghost bill-view-btn" onclick="openBillViewer(decodeURIComponent('${encodeURIComponent(x.billUrl)}'))">View Bill</button>`:''}</span>
     <span><b>${expenseDateLabel(x)}</b></span>
     <span><b>AED ${Number(x.amount||0).toFixed(2)}</b></span>
     <span>${esc(x.category||'General')}<br><small class=muted>${cashCardMethod(x,'expense')}</small></span>
     <span><small class=muted>${esc(expenseAddedBy(x))}</small>${state.profile.role==='admin'?`<div class=actions style="margin-top:6px"><button class=ghost onclick="expenseFormById('${x.id}')">Edit</button><button class="ghost danger" onclick="delRecord('expenses','${x.id}','expense')">Delete</button></div>`:''}</span>
   </div>`).join('')||'<p class=muted>No expenses match your search/filter.</p>'}</div>
 </div>`
}"""

start = s.index("function expenses(){")
end = s.index("\n\nwindow.expenseForm=", start)
s = s[:start] + expense_fn + s[end:]


old_select = '<select id=expenseMethod><option value="CASH">Cash</option><option value="CARD">Card</option></select>'
new_select = '<select id=expenseMethod><option value="CASH" ${String(x.paymentMethod||\'CASH\').toUpperCase()===\'CASH\'?\'selected\':\'\'}>Cash</option><option value="CARD" ${String(x.paymentMethod||\'\').toUpperCase()===\'CARD\'?\'selected\':\'\'}>Card</option></select>'
if old_select not in s:
    raise SystemExit("Expense payment-method selector not found")
s = s.replace(old_select, new_select, 1)

old_payment_dates = """function paymentSortTime(x){try{return Number(x?.createdAt?.toMillis?.()||x?.updatedAt?.toMillis?.()||x?.createdAt?.seconds*1000||x?.updatedAt?.seconds*1000||0)}catch{return 0}}
function paymentDateLabel(x){try{const d=x?.createdAt?.toDate?.()||x?.updatedAt?.toDate?.();return d?d.toLocaleDateString('en-GB'):'Date not recorded'}catch{return'Date not recorded'}}"""
new_payment_dates = """function paymentSortTime(x){const d=a2Date(x?.createdAt)||a2Date(x?.updatedAt);return d?d.getTime():0}
function paymentDateLabel(x){const d=a2Date(x?.createdAt)||a2Date(x?.updatedAt);return d?d.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Dubai'}):'Date not recorded'}"""
if old_payment_dates not in s:
    raise SystemExit("Payment date block not found")
s = s.replace(old_payment_dates, new_payment_dates, 1)

old_month = "function currentBillingMonth(){return monthKey(new Date())}"
new_month = "function currentBillingMonth(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Dubai',year:'numeric',month:'2-digit'}).formatToParts(new Date()),y=p.find(x=>x.type==='year')?.value,m=p.find(x=>x.type==='month')?.value;return y&&m?y+'-'+m:monthKey(new Date())}"
if old_month not in s:
    raise SystemExit("Current billing month function not found")
s = s.replace(old_month, new_month, 1)

css = """<style id="a2-techmanz-expense-parity">
.expense-head,.expense-row{display:grid;grid-template-columns:minmax(190px,2fr) minmax(135px,1.15fr) minmax(90px,.8fr) minmax(135px,1fr) minmax(160px,1.2fr);gap:10px;align-items:center}
.expense-head{padding:10px 12px;color:#91b4a7;font-size:11px;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #6ef1b51d}
.expense-row{padding:12px}
@media(max-width:900px){.expense-head{display:none}.expense-row{grid-template-columns:1fr 1fr}.expense-row>span:first-child,.expense-row>span:last-child{grid-column:1/-1}}
@media(max-width:560px){.expense-row{grid-template-columns:1fr}.expense-row>span{grid-column:1!important}}
</style>"""
if 'id="a2-techmanz-expense-parity"' not in s:
    s = s.replace("</head>", css + "\n</head>", 1)

# Mobile login must work directly from the rendered HTML, without waiting for
# a post-render helper to mutate the fields.
login_old = '<div class="field span2"><label>Email</label><input id=email type=email></div><div class="field span2"><label>Password</label><input id=pass type=password></div>'
login_new = '<div class="field span2"><label for=email>Email</label><input id=email name=a2_login_email type=text inputmode=email autocomplete=off autocapitalize=none autocorrect=off spellcheck=false enterkeyhint=next virtualkeyboardpolicy=auto></div><div class="field span2"><label for=pass>Password</label><input id=pass name=a2_login_password type=password inputmode=text autocomplete=off autocapitalize=none autocorrect=off spellcheck=false enterkeyhint=go virtualkeyboardpolicy=auto></div>'
if login_old not in s:
    raise SystemExit("Login field block not found")
s = s.replace(login_old, login_new, 1)

login_css = """<style id="a2-mobile-input-v2">
#email,#pass{position:relative!important;z-index:5!important;pointer-events:auto!important;touch-action:auto!important;-webkit-user-select:text!important;user-select:text!important;caret-color:#59f3b0!important}
.center .panel .field{position:relative;z-index:4}
@media(max-width:900px){#email,#pass{font-size:16px!important;min-height:48px!important}}
</style>"""
if 'id="a2-mobile-input-v2"' not in s:
    s = s.replace("</head>", login_css + "\n</head>", 1)

# Remove migration/developer notes from the real user-facing application.
s=s.replace('<div class=note style="margin-top:12px">The Users page now combines Firestore user profiles with linked Member records, so an existing login cannot disappear from this list just because its profile/link data is incomplete.</div>','')
s=s.replace('<div class=note style="margin-top:12px"><b>What is saved:</b> current Members, Inventory and Meals snapshots, plus Payments and Expenses for the selected month. Expense bill-image links are included. local authentication passwords are never included.</div>','')
s=s.replace('Role-based access and local authentication','Role-based account security')
s=s.replace('Meal skip cloud save failed','Meal skip save failed')

required = [
    "Added Date", "Added By / Actions", "function a2Date(v,depth=0)",
    "timeZone:'Asia/Dubai'", "Date not recorded",
    "inputmode=email", "autocomplete=off", 'id="a2-mobile-input-v2"',
    "function expenses()", "function payments()", "function memberSummary(",
    "function monthClosePage()", "function mealSkipPage()", "function backupPage()",
    "function reports()", "function users()", "function members()",
    "Kitchen Meal Count", "monthlyClosings", "mealSkips", "planByMonth",
    "manualCarryByMonth", "ACCOUNT_TRANSFER", "a2-live-notifications", "input-hardening.js"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit("Parity hardening missing markers: " + ", ".join(missing))

app.write_text(s)

sw = app.parent / "sw.js"
if sw.exists():
    t = sw.read_text()
    t, n = re.subn(r"const BUILD='[^']+'", "const BUILD='techmanz-final-ui-auth-20260927'", t, count=1)
    if n != 1:
        raise SystemExit("Service-worker BUILD marker not found")
    sw.write_text(t)

print("TECH MANZ full live parity hardening applied")
