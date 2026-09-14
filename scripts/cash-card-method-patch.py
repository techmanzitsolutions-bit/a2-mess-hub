from pathlib import Path
import re,sys
p=Path('/tmp/a2-pwa/www/app.html')
if not p.exists(): p=Path('www/app.html')
s=p.read_text()
def add_select_after_amount(block,label,field_id,options):
    marker='<div class=span2><button'
    sel=f'<div class=field><label>{label}</label><select id={field_id}>{options}</select></div>'
    if field_id not in block and marker in block:block=block.replace(marker,sel+marker,1)
    return block
forms=[('expenseForm','Paid By','expenseMethod','<option value="CASH">Cash</option><option value="CARD">Card</option>'),('paymentForm','Received By','paymentMethod','<option value="CASH">Cash</option><option value="ACCOUNT_TRANSFER">Account Transfer</option>')]
for fn,label,fid,options in forms:
    a=s.find('window.'+fn+'=')
    if a<0:a=s.find('function '+fn+'(')
    if a>=0:
        b=s.find('\nwindow.',a+10)
        if b<0:b=s.find('\nfunction ',a+10)
        if b<0:b=min(len(s),a+7000)
        part=s[a:b];part=add_select_after_amount(part,label,fid,options);s=s[:a]+part+s[b:]
s=re.sub(r"addDoc\(collection\(db,'expenses'\),\{([^{}]*?)\}\)",lambda m:"addDoc(collection(db,'expenses'),{"+m.group(1)+((',' if m.group(1).strip() and not m.group(1).rstrip().endswith(',') else '')+"paymentMethod:($('expenseMethod')?.value||'CASH')")+"})" if 'paymentMethod' not in m.group(1) else m.group(0),s)
s=re.sub(r"addDoc\(collection\(db,'payments'\),\{([^{}]*?)\}\)",lambda m:"addDoc(collection(db,'payments'),{"+m.group(1)+((',' if m.group(1).strip() and not m.group(1).rstrip().endswith(',') else '')+"paymentMethod:($('paymentMethod')?.value||'CASH')")+"})" if 'paymentMethod' not in m.group(1) else m.group(0),s)
helper="""\nfunction cashCardMethod(x,kind){const m=String(x?.paymentMethod||'').toUpperCase();if(kind==='expense')return m==='CARD'?'Paid by Card':m==='CASH'?'Paid by Cash':'Method not recorded';return (m==='ACCOUNT_TRANSFER'||m==='CARD')?'Received by Account Transfer':m==='CASH'?'Received by Cash':'Method not recorded'}\n"""
if 'function cashCardMethod(' not in s:
    pos=s.find('function dashboard(){')
    if pos>0:s=s[:pos]+helper+s[pos:]
a=s.find('function reports(){')
if a>=0:
    b=s.find('\nfunction ',a+20)
    if b<0:b=len(s)
    part=s[a:b]
    if 'Cash / Card Summary' not in part and 'Cash / Account Transfer Summary' not in part:
        end=part.rfind('`')
        if end>0:
            card="""<div class=card style=\"margin-top:12px\"><b>Cash / Account Transfer Summary</b><div class=grid>${metric('Mess · Cash','AED '+money((state.data.payments||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CASH').reduce((a,x)=>a+Number(x.amount||x.paidAmount||0),0)))}${metric('Mess · Account Transfer','AED '+money((state.data.payments||[]).filter(x=>['ACCOUNT_TRANSFER','CARD'].includes(String(x.paymentMethod||'').toUpperCase())).reduce((a,x)=>a+Number(x.amount||x.paidAmount||0),0)))}${metric('Expense · Cash','AED '+money((state.data.expenses||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CASH').reduce((a,x)=>a+Number(x.amount||0),0)))}${metric('Expense · Card','AED '+money((state.data.expenses||[]).filter(x=>String(x.paymentMethod||'').toUpperCase()==='CARD').reduce((a,x)=>a+Number(x.amount||0),0)))}</div></div>"""
            part=part[:end]+card+part[end:];s=s[:a]+part+s[b:]
if 'expenseMethod' not in s or 'paymentMethod' not in s: raise SystemExit('Payment method selectors not applied')
p.write_text(s)
print('Applied Cash/Account Transfer for mess receipts and Cash/Card for expenses')
