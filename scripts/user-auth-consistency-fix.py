from pathlib import Path

app=Path('/tmp/a2-pwa/www/app.html')
if not app.exists(): app=Path('www/app.html')
s=app.read_text()

# Do not prefill a new login email from the Member record. Member contact email can be stale
# and is not authoritative for Firebase Authentication.
s=s.replace("<input id=uemail type=email value=\"${esc(linked?.email||'')}\">","<input id=uemail type=email value=\"${esc(u.email||'')}\" autocomplete=\"off\" placeholder=\"Login email\">")
s=s.replace("if($('uemail')&&!$('uemail').value)$('uemail').value=m.email||'';","")

# Explain the Auth/profile distinction in the admin UI.
s=s.replace("Admin creates Member/Chef accounts and links Member logins to existing member records.","Admin manages app profiles linked to Firebase login accounts. Removing an app profile does not delete the Firebase Authentication login.")
s=s.replace("For Member users, choose an existing Member record. Name, plan, phone and member balance data stay connected to that member record.","Member contact details and Firebase login credentials are separate. A removed profile can still have a Firebase Authentication login until that Auth account is deleted by an administrator backend.")

# Make create failures explicit: if Auth exists but profile is missing, tell admin exactly what happened.
old="}catch(e){try{await signOut(creatorAuth)}catch{}err(e)}};"
new="}catch(e){try{await signOut(creatorAuth)}catch{}if(e?.code==='auth/email-already-in-use')return toast('This email already has a Firebase login. Do not create it again; restore/link its app profile or delete the Auth account first.');err(e)}};"
if old not in s: raise SystemExit('saveUser catch marker not found')
s=s.replace(old,new,1)

# Clarify Remove action before admin creates orphan Auth identities accidentally.
s=s.replace("Remove this user profile? The Firebase Auth login will remain, but app access will stop.","Remove only this app profile? IMPORTANT: the Firebase Authentication login will NOT be deleted and this email may still sign in to Firebase. Use Disable if you only want to block app access.")
s=s.replace("User profile removed; member record kept","App profile removed only; Firebase Auth login still exists")

required=['autocomplete=\"off\" placeholder=\"Login email\"','Member contact details and Firebase login credentials are separate','auth/email-already-in-use','App profile removed only; Firebase Auth login still exists']
missing=[x for x in required if x not in s]
if missing: raise SystemExit('Missing user consistency markers: '+', '.join(missing))
app.write_text(s)
print('Fixed stale login-email prefilling and clarified Auth/profile consistency')
