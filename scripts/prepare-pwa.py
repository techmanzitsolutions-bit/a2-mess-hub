from pathlib import Path
import subprocess, sys, shutil, os

ROOT = Path.cwd()
OUT = Path('/tmp/a2-pwa')
WWW = OUT / 'www'
SHA = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GITHUB_SHA', 'dev')

if OUT.exists():
    shutil.rmtree(OUT)
WWW.mkdir(parents=True, exist_ok=True)
for p in (ROOT / 'www').iterdir():
    dst = WWW / p.name
    if p.is_dir(): shutil.copytree(p, dst)
    else: shutil.copy2(p, dst)

workflow = subprocess.check_output([
    'git','show',
    'adc9c41d296912d71f147431aaf636fbe80b9602:.github/workflows/build-expense-columns.yml'
], text=True)
lines = workflow.splitlines()
start = next(i for i,x in enumerate(lines) if x.strip() == '- name: Create Android project')
py_start = next(i for i in range(start+1, len(lines)) if lines[i].strip() == "python - <<'PY'")
py_end = next(i for i in range(py_start+1, len(lines)) if lines[i].strip() == 'PY')
body = '\n'.join(x[10:] if x.startswith('          ') else x for x in lines[py_start+1:py_end]) + '\n'
feature_patch = Path('/tmp/a2-feature-patch.py')
feature_patch.write_text(body)
subprocess.run([sys.executable, str(feature_patch)], cwd=OUT, check=True)

app = WWW / 'app.html'
s = app.read_text()

marker = 'async function uploadBill(file){'
if marker not in s:
    raise SystemExit('uploadBill function not found')
start = s.index(marker)
end = s.index('\nwindow.pickExpensePhoto', start)
replacement = '''async function uploadBill(file){
  if(!file)throw new Error('Choose a bill photo first');
  if(file.type&&!file.type.startsWith('image/'))throw new Error('Bill file must be an image');
  const blob=await compressImage(file),fd=new FormData();
  fd.append('file',blob,'bill.jpg');
  fd.append('upload_preset','a2_mess_bills');
  fd.append('folder','A2-MESS-HUB/Bills');
  const res=await fetch('https://api.cloudinary.com/v1_1/rtsrjhpm/image/upload',{method:'POST',body:fd});
  if(!res.ok){let detail='';try{detail=await res.text()}catch{}throw new Error('Photo upload failed ('+res.status+')'+(detail?' '+detail.slice(0,140):''))}
  const j=await res.json();
  if(!j.secure_url||!j.public_id)throw new Error('Upload completed but Cloudinary did not return a photo URL');
  return{billUrl:j.secure_url,billFileId:j.public_id,imageProvider:'cloudinary'}
}'''
s = s[:start] + replacement + s[end:]
s = s.replace('Bill photos sync live using Uploadcare','Bill photos sync live using Cloudinary')
s = s.replace("imageProvider:billUrl?'uploadcare':'',updatedAt:serverTimestamp()", "imageProvider:billUrl?(billUrl.includes('res.cloudinary.com')?'cloudinary':(old.imageProvider||'uploadcare')):'',updatedAt:serverTimestamp()")
s = s.replace("({billUrl,billFileId}=await uploadBill(f));", "{const uploaded=await uploadBill(f);billUrl=uploaded.billUrl;billFileId=uploaded.billFileId;}")

s = s.replace(
"import{getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-firestore.js';",
"import{getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch,query,where}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-firestore.js';")
old_listen = "function listen(){state.unsubs.forEach(f=>f());state.unsubs=[];state.unsubs.push(onSnapshot(doc(db,'system','config'),s=>{state.config=s.data()||{};render()}));['members','inventory','meals','expenses','payments'].forEach(c=>state.unsubs.push(onSnapshot(collection(db,c),s=>{state.data[c]=s.docs.map(d=>({id:d.id,...d.data()}));render()})));if(state.profile.role==='admin')state.unsubs.push(onSnapshot(collection(db,'users'),s=>{state.data.users=s.docs.map(d=>({id:d.id,...d.data()}));render()}))}"
new_listen = "function listen(){state.unsubs.forEach(f=>f());state.unsubs=[];state.unsubs.push(onSnapshot(doc(db,'system','config'),x=>{state.config=x.data()||{};render()},err));['members','inventory','meals','expenses'].forEach(c=>state.unsubs.push(onSnapshot(collection(db,c),x=>{state.data[c]=x.docs.map(d=>({id:d.id,...d.data()}));render()},err)));if(state.profile.role==='admin'){state.unsubs.push(onSnapshot(collection(db,'payments'),x=>{state.data.payments=x.docs.map(d=>({id:d.id,...d.data()}));render()},err));state.unsubs.push(onSnapshot(collection(db,'users'),x=>{state.data.users=x.docs.map(d=>({id:d.id,...d.data()}));render()},err))}else if(state.profile.role==='member'){state.unsubs.push(onSnapshot(query(collection(db,'payments'),where('uid','==',auth.currentUser.uid)),x=>{state.data.payments=x.docs.map(d=>({id:d.id,...d.data()}));render()},err))}else{state.data.payments=[]}}"
if old_listen not in s:
    raise SystemExit('listen function not found for final launch patch')
s = s.replace(old_listen, new_listen)

helper_marker = "function expenseDate(x){"
preview_helper = "function billPreviewUrl(x,size=300){const u=resolvedBillUrl(x);if(!u)return '';if(u.includes('res.cloudinary.com/'))return u.replace('/upload/','/upload/f_auto,q_auto,c_limit,w_'+size+',h_'+size+'/');return u+'-/preview/'+size+'x'+size+'/'}\n"
if preview_helper.strip() not in s:
    if helper_marker not in s:
        raise SystemExit('expenseDate marker not found')
    s = s.replace(helper_marker, preview_helper + helper_marker)
s = s.replace('src="${esc(u)}-/preview/300x300/"', 'src="${esc(billPreviewUrl(x,300))}"')
s = s.replace("resolvedBillUrl(x)?resolvedBillUrl(x)+'-/preview/800x800/':''", "billPreviewUrl(x,800)")

# Premium animated A2 logo: chef cap flies in, cutlery rises, two leaves grow and gold orbit glows.
logo_css = r'''<style id="a2-premium-logo-style">
.a2-logo-stage{position:relative;width:min(330px,82vw);margin:0 auto 6px;filter:drop-shadow(0 18px 34px #0009);isolation:isolate}.a2-logo-stage.compact{width:118px;margin:0 0 10px}.a2-logo-svg{display:block;width:100%;height:auto;overflow:visible}.a2-orbit{fill:none;stroke:url(#a2gold);stroke-width:2.5;stroke-linecap:round;stroke-dasharray:18 10;opacity:0;transform-origin:180px 140px;animation:a2OrbitIn 1.3s .9s ease-out forwards,a2OrbitSpin 12s 2.2s linear infinite}.a2-cap{opacity:0;transform-origin:110px 70px;animation:a2CapFly 1s .12s cubic-bezier(.16,.9,.3,1.2) forwards}.a2-letterA{opacity:0;transform-origin:128px 150px;animation:a2Rise .85s .42s cubic-bezier(.2,.9,.25,1.12) forwards}.a2-letter2{opacity:0;transform-origin:235px 145px;animation:a2Right .9s .55s cubic-bezier(.2,.9,.25,1.12) forwards}.a2-fork{opacity:0;animation:a2Cutlery .7s .95s ease-out forwards}.a2-spoon{opacity:0;animation:a2Cutlery .7s 1.08s ease-out forwards}.a2-leaf-left,.a2-leaf-right{opacity:0;transform-box:fill-box;transform-origin:bottom center;animation:a2LeafGrow .85s 1.22s cubic-bezier(.2,.8,.2,1.25) forwards}.a2-leaf-right{animation-delay:1.38s}.a2-brand-word{opacity:0;animation:a2WordIn .7s 1.65s ease-out forwards}.a2-brand-tag{opacity:0;animation:a2WordIn .7s 1.95s ease-out forwards}.a2-spark{fill:#ffe6a3;opacity:0;animation:a2Spark 2.2s 1.45s ease-in-out infinite}.a2-spark.s2{animation-delay:1.75s}.a2-spark.s3{animation-delay:2.05s}@keyframes a2CapFly{0%{opacity:0;transform:translate(-120px,-95px) rotate(-24deg) scale(.45)}65%{opacity:1;transform:translate(7px,5px) rotate(5deg) scale(1.07)}100%{opacity:1;transform:none}}@keyframes a2Rise{0%{opacity:0;transform:translateY(70px) scale(.72)}100%{opacity:1;transform:none}}@keyframes a2Right{0%{opacity:0;transform:translateX(105px) rotate(18deg) scale(.72)}100%{opacity:1;transform:none}}@keyframes a2Cutlery{0%{opacity:0;transform:translateY(65px) scale(.7)}100%{opacity:1;transform:none}}@keyframes a2LeafGrow{0%{opacity:0;transform:scale(.05) rotate(-10deg)}60%{opacity:1;transform:scale(1.12) rotate(3deg)}100%{opacity:1;transform:scale(1) rotate(0)}}@keyframes a2OrbitIn{to{opacity:.8}}@keyframes a2OrbitSpin{to{transform:rotate(360deg)}}@keyframes a2WordIn{0%{opacity:0;transform:translateY(13px);filter:blur(8px)}100%{opacity:1;transform:none;filter:none}}@keyframes a2Spark{0%,100%{opacity:0;transform:scale(.3)}45%{opacity:1;transform:scale(1.5)}70%{opacity:.15;transform:scale(.7)}}@media(prefers-reduced-motion:reduce){.a2-logo-stage *{animation-duration:.01ms!important;animation-delay:0ms!important;animation-iteration-count:1!important;opacity:1!important;transform:none!important}}
</style>'''
logo_markup = r'''<div class="a2-logo-stage"><svg class="a2-logo-svg" viewBox="0 0 360 300" role="img" aria-label="A2 MESS HUB logo"><defs><linearGradient id="a2gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff2b4"/><stop offset=".34" stop-color="#f7c95e"/><stop offset=".72" stop-color="#d89925"/><stop offset="1" stop-color="#fff0a6"/></linearGradient><linearGradient id="a2green" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a9ff7a"/><stop offset=".5" stop-color="#36d86f"/><stop offset="1" stop-color="#0a8e49"/></linearGradient><filter id="a2glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><ellipse class="a2-orbit" cx="180" cy="142" rx="142" ry="76"/><g class="a2-cap" fill="url(#a2gold)" stroke="#fff1b0" stroke-width="2"><path d="M78 70c-22-4-25-36 0-43 7-22 39-25 50-6 19-13 46 4 42 24 21 8 15 38-7 39H90c-5-1-9-6-12-14z"/><path d="M88 76h73l-7 22H95z"/></g><text class="a2-letterA" x="69" y="214" font-family="Arial Black,Arial,sans-serif" font-size="154" font-weight="900" fill="url(#a2gold)" stroke="#f4d475" stroke-width="1">A</text><text class="a2-letter2" x="184" y="214" font-family="Arial Black,Arial,sans-serif" font-size="154" font-weight="900" fill="url(#a2gold)" stroke="#f4d475" stroke-width="1">2</text><g class="a2-fork" stroke="#071711" stroke-width="7" stroke-linecap="round" fill="none"><path d="M117 115v70"/><path d="M104 115v31c0 12 26 12 26 0v-31"/><path d="M111 115v26M123 115v26"/></g><g class="a2-spoon" fill="#071711"><ellipse cx="147" cy="132" rx="13" ry="20"/><rect x="143" y="147" width="8" height="42" rx="4"/></g><path class="a2-leaf-left" d="M178 213C141 173 99 176 82 207c31 11 65 15 96 6z" fill="url(#a2green)" stroke="#b7ff89" stroke-width="2"/><path class="a2-leaf-right" d="M179 213c37-40 78-37 98-8-31 15-65 18-98 8z" fill="url(#a2green)" stroke="#b7ff89" stroke-width="2"/><path d="M177 214c-24-14-47-23-69-25M181 214c23-15 46-23 69-26" fill="none" stroke="#0f7d42" stroke-width="3"/><circle class="a2-spark" cx="55" cy="126" r="4" filter="url(#a2glow)"/><circle class="a2-spark s2" cx="304" cy="101" r="3.5" filter="url(#a2glow)"/><circle class="a2-spark s3" cx="278" cy="221" r="3" filter="url(#a2glow)"/><text class="a2-brand-word" x="180" y="258" text-anchor="middle" font-family="Arial,sans-serif" font-size="31" font-weight="900" letter-spacing="5" fill="#f8cf67">MESS <tspan fill="#57e887">HUB</tspan></text><text class="a2-brand-tag" x="180" y="282" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" font-weight="700" letter-spacing="3" fill="#dff8ec">GOOD FOOD • BETTER TOGETHER</text></svg></div>'''

if 'id="a2-premium-logo-style"' not in s:
    s = s.replace('</head>', logo_css + '\n</head>')
# Initial cloud-loading splash.
s = s.replace('<div class="steam">♨️ 🍲 ♨️</div><div class="logo">A2</div><h1 class="title">MESS HUB</h1><p class="sub">Eat • Track • Manage • Sync</p>', logo_markup + '<p class="sub">Eat • Track • Manage • Sync</p>')
# Login / owner setup screen.
s = s.replace('<div class=steam>♨️ 🍲 ♨️</div><div class=logo>A2</div><h1 class=title>MESS HUB</h1><p class=sub>Cloud synchronized mess management</p>', logo_markup + '<p class=sub>Cloud synchronized mess management</p>')
# Sidebar gets a compact static-style mark while preserving fast navigation.
s = s.replace('<div class=brand>A2 MESS HUB</div>', '<div class=brand style="display:flex;align-items:center;gap:9px"><span style="display:grid;place-items:center;width:34px;height:34px;border:1px solid #f6cb6755;border-radius:10px;background:#06140f;color:#f6cb67;font-weight:1000;box-shadow:0 0 18px #f6cb6720">A2</span><span>A2 MESS HUB</span></div>')

app.write_text(s)

# Static logo asset used by browser/PWA icon surfaces.
logo_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff2b4"/><stop offset=".45" stop-color="#f7c95e"/><stop offset="1" stop-color="#d89925"/></linearGradient><linearGradient id="l" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9dff73"/><stop offset="1" stop-color="#0c9a50"/></linearGradient></defs><rect width="512" height="512" rx="116" fill="#06140f"/><circle cx="256" cy="256" r="214" fill="#0b241b" stroke="#f7c95e" stroke-width="8"/><path d="M135 135c-34-8-36-54 1-65 12-34 60-38 78-8 29-18 67 6 61 37 31 12 22 57-11 59H153c-8-2-14-10-18-23z" fill="url(#g)"/><text x="95" y="352" font-family="Arial Black,Arial,sans-serif" font-size="270" font-weight="900" fill="url(#g)">A2</text><path d="M255 352c-55-61-113-54-139-10 45 23 92 29 139 10zM257 352c54-59 111-54 139-12-45 24-92 30-139 12z" fill="url(#l)"/><text x="256" y="428" text-anchor="middle" font-family="Arial,sans-serif" font-size="36" font-weight="900" letter-spacing="6" fill="#f7d477">MESS HUB</text></svg>'''
(WWW/'a2-logo.svg').write_text(logo_svg)

manifest = '''{
  "id":"./",
  "name":"A2 MESS HUB",
  "short_name":"A2 MESS HUB",
  "description":"Eat • Track • Manage • Sync — Powered by TECHMANZ",
  "start_url":"./",
  "scope":"./",
  "display":"standalone",
  "orientation":"portrait-primary",
  "background_color":"#020907",
  "theme_color":"#06140f",
  "icons":[{"src":"./a2-logo.svg","sizes":"any","type":"image/svg+xml","purpose":"any maskable"}]
}\n'''
(WWW/'manifest.webmanifest').write_text(manifest)
(WWW/'pwa.js').write_text("""(()=>{let r=false;if('serviceWorker'in navigator){window.addEventListener('load',async()=>{try{const x=await navigator.serviceWorker.register('./sw.js',{scope:'./'});x.update().catch(()=>{})}catch(e){console.warn(e)}});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(r)return;r=true;location.reload()})}})();\n""")
(WWW/'sw.js').write_text(f"""const BUILD='{SHA}';const CACHE=`a2-mess-hub-${{BUILD}}`;const CORE=['./','./index.html','./app.html','./mobile-fixes.css','./manifest.webmanifest','./pwa.js','./a2-logo.svg'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('a2-mess-hub-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));self.addEventListener('fetch',e=>{{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==location.origin)return;e.respondWith(fetch(e.request).then(r=>{{if(r&&r.ok){{const x=r.clone();caches.open(CACHE).then(c=>c.put(e.request,x))}}return r}}).catch(()=>caches.match(e.request).then(x=>x||caches.match('./index.html'))))}});\n""")

head = '<link rel="manifest" href="./manifest.webmanifest"><link rel="icon" href="./a2-logo.svg" type="image/svg+xml"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="A2 MESS HUB">'
script = '<script src="./pwa.js" defer></script>'
for name in ('index.html','app.html'):
    p = WWW / name
    t = p.read_text()
    if 'manifest.webmanifest' not in t: t = t.replace('</head>', head+'\n</head>')
    elif 'a2-logo.svg' not in t: t = t.replace('</head>', '<link rel="icon" href="./a2-logo.svg" type="image/svg+xml">\n</head>')
    if 'src="./pwa.js"' not in t: t = t.replace('</body>', script+'\n</body>')
    p.write_text(t)

final = app.read_text()
required = [
    'api.cloudinary.com/v1_1/rtsrjhpm/image/upload',
    "upload_preset','a2_mess_bills",
    'Total Receivable',
    'Expense Name',
    'Added By',
    "where('uid','==',auth.currentUser.uid)",
    'function billPreviewUrl(x,size=300)',
    "imageProvider:'cloudinary'",
    'a2-premium-logo-style',
    'a2-cap',
    'a2-leaf-left',
    'GOOD FOOD • BETTER TOGETHER'
]
for token in required:
    if token not in final:
        raise SystemExit(f'Missing required feature: {token}')
if 'src="${esc(u)}-/preview/300x300/"' in final:
    raise SystemExit('Old Uploadcare-only expense thumbnail syntax still present')
print('A2 MESS HUB PWA prepared successfully: animated logo + Cloudinary + privacy + synced branding')
