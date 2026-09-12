from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]: paths=[Path('www/app.html')]

for app in paths:
    s=app.read_text()
    marker='function expenses(){'
    if marker not in s: raise SystemExit('expenses() marker not found')
    start=s.index(marker)
    end=s.index('\nwindow.expenseForm=',start)
    new=r'''function expenseDateKey(x){const t=x.createdAt?.toDate?.()||x.updatedAt?.toDate?.();return t instanceof Date&&!isNaN(t)?t.getTime():0}
function expenseDateLabel(x){const t=x.createdAt?.toDate?.()||x.updatedAt?.toDate?.();return t instanceof Date&&!isNaN(t)?t.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Dubai'}):'—'}
window.setExpenseView=(key,val)=>{window._expenseView={...(window._expenseView||{}),[key]:val};render()};
function expenses(){const v=window._expenseView||{},q=String(v.q||'').trim().toLowerCase(),cat=v.cat||'ALL',sort=v.sort||'newest',cats=[...new Set(state.data.expenses.map(x=>String(x.category||'General').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b));let rows=state.data.expenses.filter(x=>(cat==='ALL'||String(x.category||'General')===cat)&&(!q||[x.title,x.category,x.amount,x.createdBy].some(y=>String(y??'').toLowerCase().includes(q))));rows.sort((a,b)=>sort==='oldest'?expenseDateKey(a)-expenseDateKey(b):sort==='amountHigh'?Number(b.amount||0)-Number(a.amount||0):sort==='amountLow'?Number(a.amount||0)-Number(b.amount||0):sort==='name'?String(a.title||'').localeCompare(String(b.title||'')):expenseDateKey(b)-expenseDateKey(a));return`<div class=top style="margin-top:14px"><p class=muted>Expenses ordered newest first · search and filter available</p><button class=btn onclick=expenseForm()>+ Expense</button></div><div class=card style="margin-bottom:12px"><div class=form><div class=field><label>Search</label><input value="${esc(v.q||'')}" placeholder="Search expense, category or amount…" oninput="setExpenseView('q',this.value)"></div><div class=field><label>Category</label><select onchange="setExpenseView('cat',this.value)"><option value=ALL>All Categories</option>${cats.map(c=>`<option value="${esc(c)}" ${cat===c?'selected':''}>${esc(c)}</option>`).join('')}</select></div><div class=field><label>Sort By</label><select onchange="setExpenseView('sort',this.value)"><option value=newest ${sort==='newest'?'selected':''}>Newest First</option><option value=oldest ${sort==='oldest'?'selected':''}>Oldest First</option><option value=amountHigh ${sort==='amountHigh'?'selected':''}>Amount: High → Low</option><option value=amountLow ${sort==='amountLow'?'selected':''}>Amount: Low → High</option><option value=name ${sort==='name'?'selected':''}>Name A → Z</option></select></div><div class=field><label>Results</label><div class=note>${rows.length} expense(s) · AED ${rows.reduce((a,x)=>a+Number(x.amount||0),0).toFixed(2)}</div></div></div></div><div class="card list">${rows.map(x=>`<div class=row><span><b>${esc(x.title)}</b><small class=muted> · ${expenseDateLabel(x)}</small>${x.billUrl?`<br><a href="${esc(x.billUrl)}" target=_blank rel=noopener><img class=billimg src="${esc(x.billUrl)}-/preview/300x300/" alt="Bill photo" onerror="billImageError(this)"></a><br><a class=billlink href="${esc(x.billUrl)}" target=_blank rel=noopener>View Bill</a>`:''}</span><span>AED ${Number(x.amount||0).toFixed(2)}</span><span>${esc(x.category||'General')}</span><span>${state.profile.role==='admin'?`<div class=actions><button class=ghost onclick="expenseFormById('${x.id}')">Edit</button><button class="ghost danger" onclick="delRecord('expenses','${x.id}','expense')">Delete</button></div>`:''}</span></div>`).join('')||'<p class=muted>No expenses match your search/filter.</p>'}</div>`}
'''
    s=s[:start]+new+s[end:]
    app.write_text(s)
    print('Added expense search, category filter and sorting to',app)
