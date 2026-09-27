const API='/api';
const listeners=new Set();

class CompatTimestamp{
  constructor(value){this._date=value instanceof Date?value:new Date(value);this.seconds=Math.floor(this._date.getTime()/1000)}
  toDate(){return new Date(this._date)}
  toMillis(){return this._date.getTime()}
  toJSON(){return this._date.toISOString()}
}

function hydrate(v){
  if(Array.isArray(v))return v.map(hydrate);
  if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).map(([k,x])=>[k,hydrate(x)]));
  if(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(v)){const d=new Date(v);if(!isNaN(d))return new CompatTimestamp(d)}
  return v;
}
function plain(v){
  if(v instanceof CompatTimestamp)return v.toJSON();
  if(v instanceof Date)return v.toISOString();
  if(Array.isArray(v))return v.map(plain);
  if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).map(([k,x])=>[k,plain(x)]));
  return v;
}
function mainToken(){return localStorage.getItem('a2_token')||''}
async function api(path,opt={}){
  const h=new Headers(opt.headers||{});const token=mainToken();if(token)h.set('Authorization','Bearer '+token);
  if(opt.body&&!(opt.body instanceof FormData)&&!h.has('Content-Type'))h.set('Content-Type','application/json');
  const res=await fetch(API+path,{...opt,headers:h});
  if(res.status===401&&token){localStorage.removeItem('a2_token');localStorage.removeItem('a2_user');notifyAuth(null)}
  let body=null;const ct=res.headers.get('content-type')||'';body=ct.includes('json')?await res.json():await res.text();
  if(!res.ok){const e=new Error(body?.detail||body?.message||String(body||res.statusText));e.code='server/'+res.status;throw e}
  return hydrate(body);
}
function notifyAuth(user){for(const fn of listeners){try{fn(user)}catch(e){console.error(e)}}}
function storedUser(){try{return JSON.parse(localStorage.getItem('a2_user')||'null')}catch{return null}}

export function initializeApp(config,name='main'){return{name,config}}
export function getAuth(app={name:'main'}){const auth={name:app?.name||'main',currentUser:null};if(auth.name==='main'){const u=storedUser();auth.currentUser=u?{...u,uid:u.id}:null}return auth}
export function getFirestore(){return{kind:'techmanz-db'}}
export function getMessaging(){return{kind:'techmanz-messaging'}}
export async function isSupported(){return 'Notification' in window}
export async function getToken(){let t=localStorage.getItem('a2_device_token');if(!t){t=crypto.randomUUID?.()||String(Date.now())+Math.random();localStorage.setItem('a2_device_token',t)}return t}
export function onMessage(){return()=>{}}
export function serverTimestamp(){return{__server_timestamp__:true}}
export function collection(db,name){return{kind:'collection',collection:name}}
export function doc(db,collectionName,id){return{kind:'doc',collection:collectionName,id:String(id)}}
export function where(field,op,value){return{kind:'where',field,op,value}}
export function query(ref,...clauses){return{kind:'query',collection:ref.collection,clauses}}

function docSnap(id,data,exists=true){return{id,exists:()=>exists,data:()=>data}}
function colSnap(rows){return{docs:(rows||[]).map(x=>docSnap(String(x.id),hydrate(x.data||{}),true))}}

export async function getDoc(ref){
  const path=ref.collection==='system'&&ref.id==='config'&&!mainToken()?'/compat/public/system/config':'/compat/docs/'+encodeURIComponent(ref.collection)+'/'+encodeURIComponent(ref.id);
  const r=await api(path);return docSnap(String(r.id||ref.id),hydrate(r.data||{}),r.exists!==false)
}
export async function setDoc(ref,data,opt={}){return api('/compat/docs/'+encodeURIComponent(ref.collection)+'/'+encodeURIComponent(ref.id)+'?merge='+(opt?.merge?'true':'false'),{method:'PUT',body:JSON.stringify(plain(data))})}
export async function updateDoc(ref,data){return api('/compat/docs/'+encodeURIComponent(ref.collection)+'/'+encodeURIComponent(ref.id),{method:'PATCH',body:JSON.stringify(plain(data))})}
export async function deleteDoc(ref){return api('/compat/docs/'+encodeURIComponent(ref.collection)+'/'+encodeURIComponent(ref.id),{method:'DELETE'})}
export async function addDoc(ref,data){const r=await api('/compat/docs/'+encodeURIComponent(ref.collection),{method:'POST',body:JSON.stringify(plain(data))});return{id:String(r.id)}}

async function readTarget(ref){
  if(ref.kind==='doc')return getDoc(ref);
  const clause=(ref.clauses||[]).find(x=>x.kind==='where'&&x.op==='==');
  const qs=clause?'?field='+encodeURIComponent(clause.field)+'&eq='+encodeURIComponent(clause.value):'';
  const r=await api('/compat/docs/'+encodeURIComponent(ref.collection)+qs);return colSnap(r.docs||[])
}
export function onSnapshot(ref,next,error){
  let stopped=false,last='';
  const tick=async()=>{if(stopped)return;try{const snap=await readTarget(ref);const raw=ref.kind==='doc'?{id:snap.id,e:snap.exists(),d:plain(snap.data())}:snap.docs.map(d=>({id:d.id,d:plain(d.data())}));const now=JSON.stringify(raw);if(now!==last){last=now;next(snap)}}catch(e){if(error)error(e);else console.error(e)}};
  tick();const id=setInterval(tick,2500);return()=>{stopped=true;clearInterval(id)}
}

export function writeBatch(){
  const operations=[];
  return{
    set(ref,data,opt={}){operations.push({op:'set',collection:ref.collection,id:ref.id,data:plain(data),merge:!!opt.merge});return this},
    update(ref,data){operations.push({op:'update',collection:ref.collection,id:ref.id,data:plain(data),merge:true});return this},
    delete(ref){operations.push({op:'delete',collection:ref.collection,id:ref.id});return this},
    async commit(){return api('/compat/batch',{method:'POST',body:JSON.stringify({operations})})}
  }
}

export function onAuthStateChanged(auth,cb){
  const run=()=>{const u=storedUser();auth.currentUser=u?{...u,uid:u.id}:null;cb(auth.currentUser)};
  const fn=u=>{auth.currentUser=u;cb(u)};listeners.add(fn);queueMicrotask(run);return()=>listeners.delete(fn)
}
export async function signInWithEmailAndPassword(auth,email,password){
  const r=await api('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
  localStorage.setItem('a2_token',r.access_token);localStorage.setItem('a2_user',JSON.stringify(r.user));auth.currentUser={...r.user,uid:r.user.id};notifyAuth(auth.currentUser);return{user:auth.currentUser}
}
export async function signOut(auth){if(auth?.name==='main'){localStorage.removeItem('a2_token');localStorage.removeItem('a2_user');auth.currentUser=null;notifyAuth(null)}else auth.currentUser=null}
export async function createUserWithEmailAndPassword(auth,email,password){try{const r=await api('/compat/auth/create',{method:'POST',body:JSON.stringify({email,password,name:email.split('@')[0]})});auth.currentUser={uid:r.uid,email:r.email};return{user:auth.currentUser}}catch(e){if(e?.code==='server/409')e.code='auth/email-already-in-use';throw e}}
export async function sendPasswordResetEmail(auth,email){const password=window.prompt('Enter a new temporary password (8+ characters) for '+email);if(password===null)return;if(password.length<8)throw new Error('Password must be at least 8 characters');await api('/compat/auth/reset-password',{method:'POST',body:JSON.stringify({email,password})});return true}
