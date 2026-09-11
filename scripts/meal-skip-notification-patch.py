from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    marker="window.setMealSkip=async(meal,date)=>"
    if marker not in s:
        raise SystemExit('Meal skip handler not found')

    if 'function mealSkipAlertMessage(' not in s:
        helpers=r'''function cleanPhone(v){return String(v||'').replace(/\D/g,'')}
function mealSkipAlertMessage(memberName,meal,date){return `🍽️ A2 MESS HUB – MEAL SKIPPED\n\nMember: ${memberName||'Member'}\nMeal: ${meal}\nDate: ${date}\nStatus: NO NEED / SKIPPED\n\nPlease reduce the cooking quantity accordingly.\n\n⚡ Powered by TECHMANZ`}
function openMealSkipNotifications(memberName,meal,date){const msg=mealSkipAlertMessage(memberName,meal,date),cfg=state.config||{},adminPhone=cleanPhone(cfg.mealAlertAdminPhone),chefPhone=cleanPhone(cfg.mealAlertChefPhone),adminEmail=String(cfg.mealAlertAdminEmail||cfg.ownerEmail||'').trim(),chefEmail=String(cfg.mealAlertChefEmail||'').trim(),buttons=[];if(adminPhone)buttons.push(`<button class=btn onclick="window.open('https://wa.me/${adminPhone}?text=${encodeURIComponent(msg)}','_blank','noopener')">WhatsApp Admin</button>`);if(chefPhone)buttons.push(`<button class=btn onclick="window.open('https://wa.me/${chefPhone}?text=${encodeURIComponent(msg)}','_blank','noopener')">WhatsApp Chef</button>`);if(adminEmail)buttons.push(`<button class=ghost onclick="window.location.href='mailto:${encodeURIComponent(adminEmail)}?subject=${encodeURIComponent('A2 MESS HUB - Meal Skipped')}&body=${encodeURIComponent(msg)}'">Email Admin</button>`);if(chefEmail)buttons.push(`<button class=ghost onclick="window.location.href='mailto:${encodeURIComponent(chefEmail)}?subject=${encodeURIComponent('A2 MESS HUB - Meal Skipped')}&body=${encodeURIComponent(msg)}'">Email Chef</button>`);if(!buttons.length)return toast('Meal skipped. Admin has not configured WhatsApp/email notification contacts yet.');modal(`<div class=top><h3>Notify Admin & Chef</h3><button class=ghost onclick=closeM()>✕</button></div><p class=muted>Meal skip saved. Send the prepared alert using WhatsApp or email.</p><div class=actions style="margin-top:12px">${buttons.join('')}</div><div class=note style="margin-top:12px">WhatsApp/email compose is opened with the message ready. The member must tap Send. Fully automatic WhatsApp/email sending requires a WhatsApp Business API/email service.</div>`)}
window.saveMealAlertContacts=async()=>{if(state.profile?.role!=='admin')return toast('Admin only');try{await updateDoc(doc(db,'system','config'),{mealAlertAdminPhone:$('mealAlertAdminPhone').value.trim(),mealAlertAdminEmail:$('mealAlertAdminEmail').value.trim().toLowerCase(),mealAlertChefPhone:$('mealAlertChefPhone').value.trim(),mealAlertChefEmail:$('mealAlertChefEmail').value.trim().toLowerCase(),updatedAt:serverTimestamp()});toast('Meal skip notification contacts saved')}catch(e){err(e)}}
'''
        s=s.replace(marker,helpers+marker,1)

    old="toast(`${meal} marked No Need`)}catch(e){err(e)}}"
    new="toast(`${meal} marked No Need`);openMealSkipNotifications(member?.name||state.profile.name||'Member',meal,date)}catch(e){err(e)}}"
    if old in s:
        s=s.replace(old,new,1)
    elif 'openMealSkipNotifications(' not in s[s.find(marker):s.find('window.cancelMealSkip', s.find(marker))]:
        raise SystemExit('Could not attach meal skip notification prompt')

    admin_insert='''${role==='admin'?`<div class=card style="margin-top:14px"><h3 style="margin-top:0">🔔 Meal Skip Notification Setup</h3><div class=small>Used for WhatsApp/email alerts when a member skips a meal.</div><div class=form style="margin-top:12px"><div class=field><label>Admin WhatsApp</label><input id=mealAlertAdminPhone placeholder="9715..." value="${esc(state.config.mealAlertAdminPhone||'')}"></div><div class=field><label>Admin Email</label><input id=mealAlertAdminEmail type=email value="${esc(state.config.mealAlertAdminEmail||state.config.ownerEmail||'')}"></div><div class=field><label>Chef WhatsApp</label><input id=mealAlertChefPhone placeholder="9715..." value="${esc(state.config.mealAlertChefPhone||'')}"></div><div class=field><label>Chef Email</label><input id=mealAlertChefEmail type=email value="${esc(state.config.mealAlertChefEmail||'')}"></div><div class=span2><button class=btn onclick="saveMealAlertContacts()">SAVE NOTIFICATION CONTACTS</button></div></div></div>`:''}'''
    anchor="<div class=card style=\"margin-top:14px\"><h3 style=\"margin-top:0\">Skipped Members</h3>"
    if 'Meal Skip Notification Setup' not in s:
        if anchor not in s:
            raise SystemExit('Skipped Members anchor not found')
        s=s.replace(anchor,admin_insert+anchor,1)

    required=['function mealSkipAlertMessage(','openMealSkipNotifications(','window.saveMealAlertContacts=async','Meal Skip Notification Setup','WhatsApp Admin','Email Chef','Fully automatic WhatsApp/email sending requires']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Meal notification patch missing: '+', '.join(missing))
    app.write_text(s)
    print(f'Added meal skip WhatsApp/email notification workflow to {app}')
