from pathlib import Path
import re, shutil, sys

src=Path(sys.argv[1] if len(sys.argv)>1 else 'migration/generated-live')
out=Path(sys.argv[2] if len(sys.argv)>2 else 'migration/techmanz-build')
adapter=Path(sys.argv[3] if len(sys.argv)>3 else 'migration/frontend/techmanz-compat.js')
if out.exists(): shutil.rmtree(out)
shutil.copytree(src,out)
shutil.copy2(adapter,out/'techmanz-compat.js')
app=out/'app.html'; s=app.read_text()

imports=re.compile(r"import\{initializeApp\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-app\.js';\s*import\{getAuth,onAuthStateChanged,signInWithEmailAndPassword,createUserWithEmailAndPassword,sendPasswordResetEmail,signOut\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-auth\.js';\s*import\{getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch,query,where\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-firestore\.js';\s*import\{getMessaging,getToken,onMessage,isSupported\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-messaging\.js';")
local_import="import{initializeApp,getAuth,onAuthStateChanged,signInWithEmailAndPassword,createUserWithEmailAndPassword,sendPasswordResetEmail,signOut,getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch,query,where,getMessaging,getToken,onMessage,isSupported}from'./techmanz-compat.js';"
s,n=imports.subn(local_import,s,1)
if n!=1: raise SystemExit('Firebase import block not found exactly once')

s=re.sub(r"const firebaseConfig=\{.*?\};\nconst DEFAULT_UPLOADCARE_KEY='[^']*';", "const firebaseConfig={provider:'techmanz-local'};\nconst DEFAULT_UPLOADCARE_KEY='';", s, count=1)

start=s.index('async function uploadBill(file){'); end=s.index('\nwindow.pickExpensePhoto',start)
replacement="""async function uploadBill(file){
  if(!file)throw new Error('Choose a bill photo first');
  if(file.type&&!file.type.startsWith('image/'))throw new Error('Bill file must be an image');
  const blob=await compressImage(file),fd=new FormData();
  fd.append('bill',blob,'bill.jpg');
  const token=localStorage.getItem('a2_token')||'';
  const res=await fetch('/api/compat/files/bills',{method:'POST',headers:token?{Authorization:'Bearer '+token}:{},body:fd});
  if(!res.ok){let detail='';try{detail=(await res.json())?.detail||''}catch{}throw new Error('Photo upload failed ('+res.status+')'+(detail?' '+detail:''))}
  return await res.json()
}"""
s=s[:start]+replacement+s[end:]
s=re.sub(r"function resolvedBillUrl\(x\)\{.*?\}\nwindow\.billImageError", "function resolvedBillUrl(x){return String(x?.billUrl||'')}\nwindow.billImageError", s, count=1, flags=re.S)
s=re.sub(r"function billPreviewUrl\(x,size=300\)\{.*?\}\nfunction expenseDate", "function billPreviewUrl(x,size=300){return resolvedBillUrl(x)}\nfunction expenseDate", s, count=1, flags=re.S)

repls={
 'Connecting to cloud...':'Connecting to TECH MANZ server...',
 'Cloud synchronized mess management':'TECH MANZ server synchronized mess management',
 'Live cloud data':'Live server data',
 'cloud ✅':'server ✅',
 'Cloud verification failed':'Server verification failed',
 'Firebase login':'server login',
 'Firebase Authentication':'local authentication',
 'Firebase did not return a notification token':'TECH MANZ server did not return a notification token',
 'Send password reset email to ':'Reset password for ',
 'Password reset email sent':'Password reset saved',
 'Cloud Sync':'Server Sync',
 'cloud authentication':'local authentication',
 "imageProvider:'uploadcare'":"imageProvider:'local'",
}
for a,b in repls.items(): s=s.replace(a,b)
app.write_text(s)

sw=out/'sw.js'
if sw.exists():
    t=sw.read_text()
    if '// firebase-messaging-sw:' in t:t=t.split('// firebase-messaging-sw:',1)[0].rstrip()+"\n"
    sw.write_text(t)

cloud=out/'cloudinary-config.js'
if cloud.exists(): cloud.unlink()

bad=['www.gstatic.com/firebasejs','api.cloudinary.com','ucarecdn.com','firebase.initializeApp','firebase.messaging()']
joined='\n'.join(p.read_text(errors='ignore') for p in out.rglob('*') if p.is_file() and p.suffix in {'.html','.js','.css','.webmanifest'})
left=[x for x in bad if x in joined]
if left: raise SystemExit('External runtime dependency remains: '+', '.join(left))
required=['Total Receivable','monthlyClosings','mealSkips','Kitchen Meal Count','selectMemberPlan','ACCOUNT_TRANSFER','techmanz-compat.js']
missing=[x for x in required if x not in joined]
if missing: raise SystemExit('Required live feature marker missing: '+', '.join(missing))
print('TECH MANZ local build generated successfully')
