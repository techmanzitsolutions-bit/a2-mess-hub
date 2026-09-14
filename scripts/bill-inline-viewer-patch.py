from pathlib import Path
import re

app=Path('/tmp/a2-pwa/www/app.html')
if not app.exists():
    app=Path('www/app.html')
if not app.exists():
    raise SystemExit('app.html not found')

s=app.read_text()

# Replace duplicate thumbnail-link + View Bill external link with one in-app View Bill button.
old=r'''${x.billUrl?`<br><a href="${esc(x.billUrl)}" target=_blank rel=noopener><img class=billimg src="${esc(x.billUrl)}-/preview/300x300/" alt="Bill photo" onerror="billImageError(this)"></a><br><a class=billlink href="${esc(x.billUrl)}" target=_blank rel=noopener>View Bill</a>`:''}'''
new=r'''${x.billUrl?`<br><button class="ghost bill-view-btn" onclick="openBillViewer(decodeURIComponent('${encodeURIComponent(x.billUrl)}'))">View Bill</button>`:''}'''

if old in s:
    s=s.replace(old,new)
else:
    # Fallback for later UI patches that retain the same two-link structure with minor spacing.
    pat=re.compile(r'''\$\{x\.billUrl\?`<br><a\s+href="\$\{esc\(x\.billUrl\)\}"\s+target=_blank\s+rel=noopener><img\s+class=billimg\s+src="\$\{esc\(x\.billUrl\)\}-/preview/300x300/"\s+alt="Bill photo"\s+onerror="billImageError\(this\)"></a><br><a\s+class=billlink\s+href="\$\{esc\(x\.billUrl\)\}"\s+target=_blank\s+rel=noopener>View Bill</a>`:''\}''')
    s,n=pat.subn(new,s)
    if n==0:
        raise SystemExit('Expense bill link pattern not found')

# Add one reusable in-app bill viewer dialog.
anchor="window.billImageError=img=>{img.style.display='none';const a=img.parentElement;if(a){a.textContent='View Bill Photo';a.className='billlink'}};"
viewer=r'''
window.openBillViewer=url=>{
  if(!url)return;
  const safe=esc(url);
  modal(`<div class="top bill-view-head"><h3 style="margin:0">Bill</h3><button class=ghost onclick=closeM()>✕</button></div><div class=bill-view-wrap><img class=bill-view-image src="${safe}-/preview/1200x1200/" alt="Bill" onerror="this.onerror=null;this.src='${safe}'"></div>`);
};
'''
if 'window.openBillViewer=url=>' not in s:
    if anchor not in s:
        raise SystemExit('Bill viewer insertion anchor not found')
    s=s.replace(anchor,anchor+viewer,1)

# Styling for responsive dialog viewer inside the app.
css='''\n<style id="a2-bill-inline-viewer">\n.bill-view-btn{margin-top:9px!important;font-weight:800!important}\n.bill-view-head{position:sticky;top:0;z-index:2;background:linear-gradient(180deg,#0b2a20,#081f18);padding-bottom:10px}\n.bill-view-wrap{display:grid;place-items:center;width:100%;min-height:220px;padding:8px 0 2px}\n.bill-view-image{display:block;max-width:100%;width:auto;height:auto;max-height:76vh;object-fit:contain;border-radius:14px;background:#020907;box-shadow:0 12px 38px #0008}\n@media(max-width:560px){.modal{padding:8px!important}.modal>.card{width:100%!important;max-height:94vh!important;padding:12px!important}.bill-view-image{max-height:78vh!important}}\n</style>\n'''
if 'id="a2-bill-inline-viewer"' not in s:
    s=s.replace('</head>',css+'</head>',1)

# Guard: expense bill viewer must not open a new tab anymore.
expense_start=s.find('function expenses(){')
expense_end=s.find('window.expenseForm=',expense_start)
if expense_start<0 or expense_end<0:
    raise SystemExit('Expense section not found')
frag=s[expense_start:expense_end]
if 'target=_blank' in frag or 'View Bill Photo' in frag or '<img class=billimg' in frag:
    raise SystemExit('Duplicate/external bill viewer still remains in expense list')
if 'openBillViewer' not in frag:
    raise SystemExit('In-app bill viewer button missing')

app.write_text(s)
print('Expense bills now use one View Bill button and open inside the app dialog')
