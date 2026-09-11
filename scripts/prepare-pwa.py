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

# Reuse the exact feature patch that produced the approved Expense Columns/member dashboard build.
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
app.write_text(s)

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
  "theme_color":"#06140f"
}\n'''
(WWW/'manifest.webmanifest').write_text(manifest)
(WWW/'pwa.js').write_text("""(()=>{let r=false;if('serviceWorker'in navigator){window.addEventListener('load',async()=>{try{const x=await navigator.serviceWorker.register('./sw.js',{scope:'./'});x.update().catch(()=>{})}catch(e){console.warn(e)}});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(r)return;r=true;location.reload()})}})();\n""")
(WWW/'sw.js').write_text(f"""const BUILD='{SHA}';const CACHE=`a2-mess-hub-${{BUILD}}`;const CORE=['./','./index.html','./app.html','./mobile-fixes.css','./manifest.webmanifest','./pwa.js'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('a2-mess-hub-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));self.addEventListener('fetch',e=>{{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==location.origin)return;e.respondWith(fetch(e.request).then(r=>{{if(r&&r.ok){{const x=r.clone();caches.open(CACHE).then(c=>c.put(e.request,x))}}return r}}).catch(()=>caches.match(e.request).then(x=>x||caches.match('./index.html'))))}});\n""")

head = '<link rel="manifest" href="./manifest.webmanifest"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="A2 MESS HUB">'
script = '<script src="./pwa.js" defer></script>'
for name in ('index.html','app.html'):
    p = WWW / name
    t = p.read_text()
    if 'manifest.webmanifest' not in t: t = t.replace('</head>', head+'\n</head>')
    if 'src="./pwa.js"' not in t: t = t.replace('</body>', script+'\n</body>')
    p.write_text(t)

final = app.read_text()
required = [
    'api.cloudinary.com/v1_1/rtsrjhpm/image/upload',
    "upload_preset','a2_mess_bills",
    'Total Receivable',
    'Expense Name',
    'Added By'
]
for token in required:
    if token not in final:
        raise SystemExit(f'Missing required feature: {token}')
print('A2 MESS HUB PWA prepared successfully with Cloudinary storage')
