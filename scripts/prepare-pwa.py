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
if old_listen in s:
    s = s.replace(old_listen, new_listen)

helper_marker = "function expenseDate(x){"
preview_helper = "function billPreviewUrl(x,size=300){const u=resolvedBillUrl(x);if(!u)return '';if(u.includes('res.cloudinary.com/'))return u.replace('/upload/','/upload/f_auto,q_auto,c_limit,w_'+size+',h_'+size+'/');return u+'-/preview/'+size+'x'+size+'/'}\n"
if preview_helper.strip() not in s and helper_marker in s:
    s = s.replace(helper_marker, preview_helper + helper_marker)
s = s.replace('src="${esc(u)}-/preview/300x300/"', 'src="${esc(billPreviewUrl(x,300))}"')
s = s.replace("resolvedBillUrl(x)?resolvedBillUrl(x)+'-/preview/800x800/':''", "billPreviewUrl(x,800)")

# Unified animated A2 branding for splash/front/login.
brand_css = '''\n<style id="a2-brand-style">\n.a2-logo-stage{position:relative;width:190px;height:190px;margin:0 auto 8px;display:grid;place-items:center;filter:drop-shadow(0 10px 30px #0008)}\n.a2-logo-stage img{width:100%;height:100%;object-fit:contain;animation:a2logoIn 1.1s cubic-bezier(.2,.9,.2,1) both,a2float 4s ease-in-out 1.1s infinite}\n.a2-logo-stage:after{content:'';position:absolute;inset:20px;border-radius:50%;border:1px solid #f6cb6733;box-shadow:0 0 34px #f6cb6720;animation:a2orbit 4.5s linear infinite}\n.a2-brand-name{text-align:center;font-weight:1000;letter-spacing:.18em;font-size:22px;margin-top:-6px}.a2-brand-name span{color:#65e66d}.a2-brand-tag{text-align:center;color:#d8c28b;font-size:11px;letter-spacing:.13em;margin-top:5px}.a2-powered{text-align:center;color:#f6cb67;font-weight:900;margin-top:12px}\n@keyframes a2logoIn{0%{opacity:0;transform:translateY(-45px) scale(.7) rotate(-7deg)}60%{opacity:1;transform:translateY(8px) scale(1.05) rotate(2deg)}100%{opacity:1;transform:none}}\n@keyframes a2float{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}@keyframes a2orbit{to{transform:rotate(360deg)}}\n@media(prefers-reduced-motion:reduce){.a2-logo-stage img,.a2-logo-stage:after{animation:none!important}}\n</style>\n'''
if 'id="a2-brand-style"' not in s:
    s=s.replace('</head>',brand_css+'</head>')
brand_block='<div class="a2-logo-stage"><img src="./logo.svg" alt="A2 MESS HUB logo"></div><div class="a2-brand-name">A2 MESS <span>HUB</span></div><div class="a2-brand-tag">GOOD FOOD • BETTER TOGETHER</div>'
s=s.replace('<div class="steam">♨️ 🍲 ♨️</div><div class="logo">A2</div><h1 class="title">MESS HUB</h1>',brand_block)
s=s.replace('<div class=steam>♨️ 🍲 ♨️</div><div class=logo>A2</div><h1 class=title>MESS HUB</h1>',brand_block)
s=s.replace('<p class=powered>⚡ POWERED BY TECHMANZ</p>','<p class="a2-powered">⚡ POWERED BY TECHMANZ</p>')
app.write_text(s)

logo_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<defs>
 <linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff1ad"/><stop offset=".38" stop-color="#f6c34f"/><stop offset="1" stop-color="#a8610d"/></linearGradient>
 <linearGradient id="l" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#b9ff6d"/><stop offset=".5" stop-color="#39c95c"/><stop offset="1" stop-color="#0f6d34"/></linearGradient>
 <filter id="glow"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect width="512" height="512" rx="112" fill="#07130f"/>
<circle cx="256" cy="256" r="202" fill="none" stroke="#f6c34f" stroke-width="6" opacity=".55"/>
<!-- chef cap -->
<path d="M139 140c-31-3-47-25-41-51 6-26 33-39 56-28 9-28 42-39 64-21 20-22 60-14 69 15 29-9 55 12 53 40-2 25-21 41-47 43l-9 33H149z" fill="#fff7dc" stroke="#e7b83f" stroke-width="8"/>
<path d="M151 148h137l-9 30H157z" fill="url(#g)"/>
<!-- A2 -->
<path d="M116 357l74-190h65l74 190h-57l-14-41h-75l-14 41zm82-88h45l-22-68z" fill="url(#g)" filter="url(#glow)"/>
<path d="M295 209c8-39 39-61 82-61 49 0 82 28 82 69 0 35-18 57-57 84l-35 24h98v32H294v-27c0-20 7-34 26-47l47-33c24-17 33-27 33-42 0-17-12-28-30-28-19 0-31 11-34 34z" fill="url(#g)"/>
<!-- fork -->
<path d="M190 218v83m-12-83v38m12-38v38m12-38v38m-24 0h24" stroke="#07130f" stroke-width="8" stroke-linecap="round" fill="none"/>
<!-- spoon -->
<ellipse cx="232" cy="239" rx="13" ry="24" fill="#07130f"/><path d="M232 261v41" stroke="#07130f" stroke-width="8" stroke-linecap="round"/>
<!-- leaves -->
<path d="M248 345c-68 14-107-10-126-57 62-5 104 10 126 57z" fill="url(#l)" stroke="#7ff58a" stroke-width="4"/><path d="M259 346c49-57 96-71 145-55-20 51-66 73-145 55z" fill="url(#l)" stroke="#7ff58a" stroke-width="4"/><path d="M177 307c31 10 51 21 72 39M338 309c-28 10-51 22-77 38" stroke="#d6ff91" stroke-width="4" fill="none" opacity=".8"/>
<!-- label -->
<text x="256" y="413" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="42" font-weight="900" letter-spacing="5" fill="#f6c34f">A2</text>
<text x="256" y="454" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="25" font-weight="800" letter-spacing="4" fill="#ffffff">MESS <tspan fill="#63df68">HUB</tspan></text>
</svg>'''
(WWW/'logo.svg').write_text(logo_svg)

manifest = '''{
  "id":"./",
  "name":"A2 MESS HUB",
  "short_name":"A2 MESS HUB",
  "description":"Eat • Track • Manage • Sync — Powered by TECHMANZ",
  "start_url":"./",
  "scope":"./",
  "display":"standalone",
  "orientation":"portrait-primary",
  "background_color":"#07130f",
  "theme_color":"#07130f",
  "icons":[{"src":"./logo.svg","sizes":"any","type":"image/svg+xml","purpose":"any maskable"}]
}\n'''
(WWW/'manifest.webmanifest').write_text(manifest)
(WWW/'pwa.js').write_text("""(()=>{let r=false;if('serviceWorker'in navigator){window.addEventListener('load',async()=>{try{const x=await navigator.serviceWorker.register('./sw.js',{scope:'./'});x.update().catch(()=>{})}catch(e){console.warn(e)}});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(r)return;r=true;location.reload()})}})();\n""")
(WWW/'sw.js').write_text(f"""const BUILD='{SHA}';const CACHE=`a2-mess-hub-${{BUILD}}`;const CORE=['./','./index.html','./app.html','./mobile-fixes.css','./manifest.webmanifest','./pwa.js','./logo.svg'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('a2-mess-hub-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));self.addEventListener('fetch',e=>{{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==location.origin)return;e.respondWith(fetch(e.request).then(r=>{{if(r&&r.ok){{const x=r.clone();caches.open(CACHE).then(c=>c.put(e.request,x))}}return r}}).catch(()=>caches.match(e.request).then(x=>x||caches.match('./index.html'))))}});\n""")

head = '<link rel="manifest" href="./manifest.webmanifest"><link rel="icon" type="image/svg+xml" href="./logo.svg"><link rel="apple-touch-icon" href="./logo.svg"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="A2 MESS HUB">'
script = '<script src="./pwa.js" defer></script>'
for name in ('index.html','app.html'):
    p = WWW / name
    t = p.read_text()
    if 'manifest.webmanifest' not in t: t = t.replace('</head>', head+'\n</head>')
    elif 'rel="icon"' not in t: t = t.replace('</head>','<link rel="icon" type="image/svg+xml" href="./logo.svg"><link rel="apple-touch-icon" href="./logo.svg">\n</head>')
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
    './logo.svg',
    'GOOD FOOD • BETTER TOGETHER'
]
for token in required:
    if token not in final:
        raise SystemExit(f'Missing required feature: {token}')
if 'src="${esc(u)}-/preview/300x300/"' in final:
    raise SystemExit('Old Uploadcare-only expense thumbnail syntax still present')
if not (WWW/'logo.svg').exists():
    raise SystemExit('Unified logo asset missing')
print('A2 MESS HUB PWA prepared successfully: unified animated splash + favicon + home-screen icon + Cloudinary')
