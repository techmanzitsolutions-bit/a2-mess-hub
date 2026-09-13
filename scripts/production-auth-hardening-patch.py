from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]: paths=[Path('www/app.html')]

for app in paths:
    s=app.read_text()
    auth_import="import{getAuth,onAuthStateChanged,signInWithEmailAndPassword,createUserWithEmailAndPassword,sendPasswordResetEmail,signOut}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-auth.js';"
    functions_import="import{getFunctions,httpsCallable}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-functions.js';"
    if functions_import not in s:
        if auth_import not in s: raise SystemExit('Firebase Auth import marker missing')
        s=s.replace(auth_import,auth_import+'\n'+functions_import,1)

    init_marker="const fb=initializeApp(firebaseConfig),auth=getAuth(fb),db=getFirestore(fb),creatorApp=initializeApp(firebaseConfig,'creator'),creatorAuth=getAuth(creatorApp),appEl=document.getElementById('app');"
    if "const functions=getFunctions(fb);" not in s:
        if init_marker not in s: raise SystemExit('Firebase initialization marker missing')
        s=s.replace(init_marker,init_marker+"\nconst functions=getFunctions(fb);",1)

    cleanup_marker="state.unsubs.forEach(f=>f());state.unsubs=[];"
    meal_listener="state.unsubs.push(onSnapshot(collection(db,'mealSkips'),snap=>{state.data.mealSkips=snap.docs.map(d=>({id:d.id,...d.data()}));render()},e=>{console.error('mealSkips realtime listener',e);toast('Meal skip sync error')}));"
    guard="state.unsubs.push(onSnapshot(doc(db,'users',auth.currentUser.uid),async snap=>{if(window._accessClosing)return;const p=snap.data();if(!snap.exists()||p.active===false||p.removed===true){window._accessClosing=true;toast('Account disabled or removed by Admin');await signOut(auth);return}state.profile={uid:snap.id,...p};render()},err));"
    # The meal-skip patch historically placed its listener before cleanup, so it
    # was immediately unsubscribed. Normalize the order while installing the
    # access-revocation listener.
    misplaced="function listen(){"+meal_listener+cleanup_marker
    if misplaced in s:
        s=s.replace(misplaced,"function listen(){"+cleanup_marker+meal_listener+guard,1)
    elif "function listen(){"+cleanup_marker in s:
        s=s.replace("function listen(){"+cleanup_marker,"function listen(){"+cleanup_marker+guard,1)
    elif guard not in s:
        raise SystemExit('Realtime listener marker missing')

    render_marker="function render(){"
    override=r'''
const callCreateManagedUser=httpsCallable(functions,'createManagedUser');
const callUpdateManagedUser=httpsCallable(functions,'updateManagedUser');
const callDeleteManagedUser=httpsCallable(functions,'deleteManagedUser');

window.saveUser=async id=>{const btn=$('userSaveBtn');try{if(btn){btn.disabled=true;btn.textContent='SAVING…'}const role=$('urole').value,memberId=role==='member'?$('umember').value:'',member=memberId?state.data.members.find(x=>String(x.id)===String(memberId)):null;if(role==='member'&&!member)return toast('Select a member to link');const name=(member?.name||$('uname').value).trim();if(!name)return toast('Enter name');if(id){await callUpdateManagedUser({uid:id,name,role,memberId});closeM();return toast('User updated securely')}const email=$('uemail').value.trim().toLowerCase(),password=$('upass').value;if(!email||password.length<8)return toast('Enter valid email and password (8+)');await callCreateManagedUser({email,password,name,role,memberId});closeM();toast('User created securely')}catch(e){const code=String(e?.code||'');if(code.includes('already-exists'))toast('This email or member is already linked. Restore it or use another email.');else err(e)}finally{if(btn){btn.disabled=false;btn.textContent='SAVE'}}};
window.toggleUser=async(id,isDisabled)=>{try{await callUpdateManagedUser({uid:id,disabled:!isDisabled});toast(isDisabled?'User enabled securely':'User disabled on all devices')}catch(e){err(e)}};
window.removeUserProfile=async id=>{if(!ask('Permanently remove this login? Firebase Authentication and app access will be deleted. The member record will be kept.'))return;try{await callDeleteManagedUser({uid:id});toast('User login permanently removed')}catch(e){err(e)}};
'''
    if 'const callCreateManagedUser=' not in s:
        if render_marker not in s: raise SystemExit('Render marker missing')
        s=s.replace(render_marker,override+'\n'+render_marker,1)

    old_check="if(!p.exists()||p.data().active===false)"
    if old_check in s: s=s.replace(old_check,"if(!p.exists()||p.data().active===false||p.data().removed===true)",1)

    required=['getFunctions,httpsCallable','callCreateManagedUser','callUpdateManagedUser','callDeleteManagedUser','User disabled on all devices','Firebase Authentication and app access will be deleted','window._accessClosing']
    missing=[x for x in required if x not in s]
    if missing: raise SystemExit('Production auth hardening missing: '+', '.join(missing))
    app.write_text(s)
    print('Applied production Firebase Auth hardening to',app)
