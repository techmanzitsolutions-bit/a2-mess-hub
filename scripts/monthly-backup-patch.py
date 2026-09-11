from pathlib import Path
import sys

paths = [Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths = [Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s = app.read_text()

    # Admin-only Backup page in navigation. Keep Member/Chef navigation unchanged.
    s = s.replace(
        "['dashboard','users','members','meals','inventory','expenses','payments','gas','reports','settings']",
        "['dashboard','users','members','meals','inventory','expenses','payments','gas','reports','backup','settings']"
    )
    s = s.replace(
        "['dashboard','users','members','meals','inventory','expenses','payments','reports','settings']",
        "['dashboard','users','members','meals','inventory','expenses','payments','reports','backup','settings']"
    )

    if "backup:'Backup'" not in s:
        if "gas:'Order Gas',reports:'Reports',settings:'Settings'" in s:
            s = s.replace(
                "gas:'Order Gas',reports:'Reports',settings:'Settings'",
                "gas:'Order Gas',reports:'Reports',backup:'Backup',settings:'Settings'"
            )
        else:
            s = s.replace(
                "reports:'Reports',settings:'Settings'",
                "reports:'Reports',backup:'Backup',settings:'Settings'"
            )

    if 'function backupPage(){' not in s:
        marker = 'function reports(){'
        if marker not in s:
            raise SystemExit('reports marker not found')
        backup = r'''function backupMonthOf(x){if(!x)return'';const explicit=String(x.billingMonth||x.month||'');if(/^\d{4}-\d{2}$/.test(explicit))return explicit;for(const k of ['date','createdAt','updatedAt']){const v=x[k];if(!v)continue;if(typeof v==='string'){const m=v.match(/^(\d{4}-\d{2})/);if(m)return m[1]}try{const d=typeof v.toDate==='function'?v.toDate():new Date(v);if(!Number.isNaN(d.getTime()))return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`}catch{}}return''}
function backupPlain(v){if(v===null||v===undefined||typeof v==='string'||typeof v==='number'||typeof v==='boolean')return v;if(v&&typeof v.toDate==='function')return{__a2Timestamp:v.toDate().toISOString()};if(v instanceof Date)return{__a2Timestamp:v.toISOString()};if(Array.isArray(v))return v.map(backupPlain);if(typeof v==='object'){const o={};Object.keys(v).forEach(k=>o[k]=backupPlain(v[k]));return o}return String(v)}
function backupRevive(v){if(v===null||v===undefined||typeof v!=='object')return v;if(Array.isArray(v))return v.map(backupRevive);if(Object.keys(v).length===1&&v.__a2Timestamp){const d=new Date(v.__a2Timestamp);return Number.isNaN(d.getTime())?v.__a2Timestamp:d}const o={};Object.keys(v).forEach(k=>o[k]=backupRevive(v[k]));return o}
function backupPage(){if(state.profile.role!=='admin')return`<div class=note style="margin-top:14px">Admin only.</div>`;const month=currentBillingMonth();return`<div class="card" style="margin-top:14px"><div class=top><div><h3 style="margin:0">🛡️ Monthly Backup</h3><div class=small>Admin-only offline copy of A2 MESS HUB records</div></div><span class=tag>JSON</span></div><div class=form style="margin-top:16px"><div class=field><label>Backup Month</label><input id=backupMonth type=month value="${month}"></div><div class=field><label>Includes</label><input value="Members, Inventory, Meals, Payments, Expenses" readonly></div><div class=span2><button class=btn style="width:100%;padding:14px" onclick=downloadMonthlyBackup()>⬇️ DOWNLOAD MONTHLY BACKUP</button></div></div><div class=note style="margin-top:12px"><b>What is saved:</b> current Members, Inventory and Meals snapshots, plus Payments and Expenses for the selected month. Expense bill-image links are included. Firebase Authentication passwords are never included.</div></div><div class="card" style="margin-top:14px"><h3 style="margin-top:0">♻️ Restore Backup</h3><div class=small>Choose an A2 MESS HUB backup JSON file. Existing records with the same IDs will be merged; missing records in the backup are not automatically deleted.</div><input id=backupFile class=filehide type=file accept="application/json,.json" onchange=restoreMonthlyBackup(this)><button class=ghost style="margin-top:14px;width:100%;padding:13px" onclick="document.getElementById('backupFile').click()">SELECT BACKUP FILE TO RESTORE</button></div><div class=note style="margin-top:14px">Recommended: download one backup at the end of every month and keep a second copy in Google Drive, OneDrive, iCloud Drive or another safe location.</div>`}
window.downloadMonthlyBackup=()=>{if(state.profile?.role!=='admin')return toast('Admin only');try{const month=$('backupMonth')?.value||currentBillingMonth(),pack={format:'A2-MESS-HUB-MONTHLY-BACKUP',version:1,month,createdAt:new Date().toISOString(),createdBy:state.profile?.email||state.profile?.name||'Admin',data:{members:state.data.members.map(backupPlain),inventory:state.data.inventory.map(backupPlain),meals:state.data.meals.map(backupPlain),payments:state.data.payments.filter(x=>backupMonthOf(x)===month).map(backupPlain),expenses:state.data.expenses.filter(x=>backupMonthOf(x)===month).map(backupPlain)}};const json=JSON.stringify(pack,null,2),blob=new Blob([json],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`A2-MESS-HUB-BACKUP-${month}.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);toast('Monthly backup downloaded')}catch(e){err(e)}};
window.restoreMonthlyBackup=async input=>{if(state.profile?.role!=='admin')return toast('Admin only');const file=input?.files?.[0];if(!file)return;try{const pack=JSON.parse(await file.text());if(pack?.format!=='A2-MESS-HUB-MONTHLY-BACKUP'||!pack?.data)throw new Error('This is not a valid A2 MESS HUB backup file');const cols=['members','inventory','meals','payments','expenses'],counts=cols.map(c=>`${c}: ${Array.isArray(pack.data[c])?pack.data[c].length:0}`).join('\n');if(!ask(`Restore A2 MESS HUB backup for ${pack.month||'unknown month'}?\n\n${counts}\n\nMatching record IDs will be merged. This will not delete records that are not in the backup.`)){input.value='';return}let batch=writeBatch(db),ops=0,total=0;for(const c of cols){for(const raw of (Array.isArray(pack.data[c])?pack.data[c]:[])){const r=backupRevive(raw);if(!r?.id)continue;const id=String(r.id),data={...r};delete data.id;batch.set(doc(db,c,id),data,{merge:true});ops++;total++;if(ops>=400){await batch.commit();batch=writeBatch(db);ops=0}}}if(ops)await batch.commit();input.value='';toast(`Backup restored: ${total} records`)}catch(e){input.value='';err(e)}};
'''
        s = s.replace(marker, backup + marker, 1)

    # Add Backup page to renderer. Support builds with or without gas page.
    s = s.replace(
        '{dashboard,users,members,meals,inventory,expenses,payments,gas:gasOrder,reports,settings}',
        '{dashboard,users,members,meals,inventory,expenses,payments,gas:gasOrder,reports,backup:backupPage,settings}'
    )
    s = s.replace(
        '{dashboard,users,members,meals,inventory,expenses,payments,reports,settings}',
        '{dashboard,users,members,meals,inventory,expenses,payments,reports,backup:backupPage,settings}'
    )

    required = [
        'function backupPage(){',
        'window.downloadMonthlyBackup=',
        'window.restoreMonthlyBackup=',
        "backup:'Backup'",
        'A2-MESS-HUB-MONTHLY-BACKUP',
        'Expense bill-image links are included',
        'backup:backupPage'
    ]
    missing = [x for x in required if x not in s]
    if missing:
        raise SystemExit('Monthly backup patch missing: ' + ', '.join(missing))

    app.write_text(s)
    print(f'Added admin monthly backup and restore to {app}')
