#!/usr/bin/env python3
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'migration/generated-live'
OUT=ROOT/'migration/techmanz-build'

if not (SRC/'app.html').exists():
    raise SystemExit('generated live baseline missing')

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC,OUT)

p=OUT/'app.html'
s=p.read_text()

imports=re.compile(
    r"import\{initializeApp\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-app\.js';\n"
    r"import\{getAuth,onAuthStateChanged,signInWithEmailAndPassword,createUserWithEmailAndPassword,sendPasswordResetEmail,signOut\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-auth\.js';\n"
    r"import\{getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch,query,where\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-firestore\.js';\n"
    r"import\{getMessaging,getToken,onMessage,isSupported\}from'https://www\.gstatic\.com/firebasejs/11\.9\.1/firebase-messaging\.js';"
)
replacement="""import{initializeApp,getAuth,onAuthStateChanged,signInWithEmailAndPassword,createUserWithEmailAndPassword,sendPasswordResetEmail,signOut,getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch,query,where,getMessaging,getToken,onMessage,isSupported}from'./techmanz-adapter.js';"""
s,n=imports.subn(replacement,s,count=1)
if n!=1:
    raise SystemExit('Firebase import block not found exactly once')

s,n=re.subn(r"const firebaseConfig=\{.*?\};", "const firebaseConfig={runtime:'techmanz'};", s, count=1)
if n!=1:
    raise SystemExit('firebaseConfig not found')
s=s.replace("const DEFAULT_UPLOADCARE_KEY='002716e9054a6ef05d45';","const DEFAULT_UPLOADCARE_KEY='';")

start=s.find('async function uploadBill(file){')
end=s.find('window.pickExpensePhoto=',start)
if start<0 or end<0:
    raise SystemExit('uploadBill block not found')
upload="""async function uploadBill(file){
  if(!file)throw new Error('Choose a bill photo first');
  if(file.type&&!['image/jpeg','image/png','application/pdf'].includes(file.type))throw new Error('Bill must be JPG, PNG or PDF');
  const blob=file.type==='application/pdf'?file:await compressImage(file);
  const fd=new FormData();fd.append('bill',blob,file.name||'bill.jpg');
  const t=localStorage.getItem('a2_token')||'';
  const res=await fetch('/api/live/bill-upload',{method:'POST',headers:t?{Authorization:'Bearer '+t}:{},body:fd});
  let j={};try{j=await res.json()}catch{}
  if(!res.ok)throw new Error(j?.detail||('Photo upload failed ('+res.status+')'));
  return{billUrl:j.billUrl,billFileId:j.billFileId,imageProvider:'local'}
}
"""
s=s[:start]+upload+s[end:]

s=s.replace('Connecting to cloud…','Connecting to TECH MANZ server…')
s=s.replace('Cloud Sync</b><span>● Connected','Server Sync</b><span>● Connected')
s=s.replace('cloud authentication','server authentication')
s=s.replace('skip saved to cloud ✅','skip saved ✅')
s=s.replace('Cloud verification failed','Server verification failed')
s=s.replace('Meal skip cloud save failed','Meal skip save failed')

p.write_text(s)
shutil.copy2(ROOT/'migration/server/web/techmanz-adapter.js',OUT/'techmanz-adapter.js')

required=[
 'Total Receivable','PARTIAL','monthlyClosings','mealSkips','Kitchen Meal Count',
 'plan-choice','selectMemberPlan','[100,200,250].includes(planAmount)',
 'ACCOUNT_TRANSFER','a2-live-notifications','tm-solutions-approved.webp'
]
missing=[x for x in required if x not in s]
if missing:
    raise SystemExit('Feature loss: '+', '.join(missing))
if 'gstatic.com/firebasejs' in s:
    raise SystemExit('Firebase runtime import remains')
if 'api.cloudinary.com' in s:
    raise SystemExit('Cloudinary upload runtime remains')
print('TECH MANZ frontend build passed')
