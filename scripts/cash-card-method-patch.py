from pathlib import Path
import re,sys
p=Path('/tmp/a2-pwa/www/app.html')
if not p.exists(): p=Path('www/app.html')
s=p.read_text()
# Add selector to Expense and Payment forms by locating their modal form markup.
def add_select_after_amount(block,label,field_id):
    # insert before first span2 save/action field after amount input
    marker='<div class=span2><button'
    sel=f'<div class=field><label>{label}</label><select id={field_id}><option value="CASH">Cash</option><option value="CARD">Card</option></select></div>'
    if field_id not in block and marker in block:block=block.replace(marker,sel+marker,1)
    return block
# Patch expenseForm/paymentForm function bodies conservatively.
for fn,label,fid in [('expenseForm','Paid By','expenseMethod'),('paymentForm','Received By','paymentMethod')]:
    a=s.find('window.'+fn+'=')
    if a<0:a=s.find('function '+fn+'(')
    if a>=0:
        b=s.find('\nwindow.',a+10)
        if b<0:b=s.find('\nfunction ',a+10)
        if b<0:b=min(len(s),a+7000)
        part=s[a:b]
        part=add_select_after_amount(part,label,fid)
        s=s[:a]+part+s[b:]
# Save method on expense addDoc payloads containing expenses collection.
s=re.sub(r"addDoc\(collection\(db,'expenses'\),\{([^{}]*?)\}\)",lambda m:"addDoc(collection(db,'expenses'),{"+m.group(1)+((',' if m.group(1).strip() and not m.group(1).rstrip().endswith(',') else '')+"paymentMethod:($('expenseMethod')?.value||'CASH')")+"})" if 'paymentMethod' not in m.group(1) else m.group(0),s)
# Save method on payment addDoc payloads.
s=re.sub(r"addDoc\(collection\(db,'payments'\),\{([^{}]*?)\}\)",lambda m:"addDoc(collection(db,'payments'),{"+m.group(1)+((',' if m.group(1).strip() and not m.group(1).rstrip().endswith(',') else '')+"paymentMethod:($('paymentMethod')?.value||'CASH')")+"})" if 'paymentMethod' not in m.group(1) else m.group(0),s)
# Add visible labels in list rows where common amount/date templates occur. Runtime-safe helper.
helper="""\nfunction cashCardMethod(x,kind){const m=String(x?.paymentMethod||'').toUpperCase();return m==='CARD'?(kind==='expense'?'Paid by Card':'Received by Card'):(m==='CASH'?(kind==='expense'?'Paid by Cash':'Received by Cash'):'Method not recorded')}\n"""
if 'function cashCardMethod(' not in s:
    pos=s.find('function dashboard(){')
    if pos>0:s=s[:pos]+helper+s[pos:]
# Enhance report page by inserting a compact month method summary before return content when identifiable.
a=s.find('function reports(){')
if a>=0:
    b=s.find('\nfunction ',a+20)
    if b<0:b=len(s)
    part=s[a:b]
    if 'Cash / Card Summary' not in part:
        # append summary card to first returned template literal
        end=part.rfind('`')
        if end>0:
            card="""<div class=card style=\"margin-top:12px\"><b>Cash / Card Summary</b><div class=grid>${metric('Mess · Cash','AED '+money((state.data.payments||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CASH').reduce((a,x)=>a+Number(x.amount||x.paidAmount||0),0)))}${metric('Mess · Card','AED '+money((state.data.payments||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CARD').reduce((a,x)=>a+Number(x.amount||x.paidAmount||0),0)))}${metric('Expense · Cash','AED '+money((state.data.expenses||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CASH').reduce((a,x)=>a+Number(x.amount||0),0)))}${metric('Expense · Card','AED '+money((state.data.expenses||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CARD').reduce((a,x)=>a+Number(x.amount||0),0)))}</div></div>"""
            part=part[:end]+card+part[end:]
            s=s[:a]+part+s[b:]
# Validation markers
if 'expenseMethod' not in s or 'paymentMethod' not in s: raise SystemExit('Cash/card selectors not applied')
p.write_text(s)
print('Applied Cash/Card method tracking for mess payments and expenses')
