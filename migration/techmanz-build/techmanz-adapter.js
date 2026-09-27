const API='/api';
const listeners=new Set();
let token=localStorage.getItem('a2_token')||'';
let authUser=null;
let pendingCreator=null;

function appError(status,body){
  const msg=body?.detail||body?.message||('Request failed ('+status+')');
  const e=new Error(typeof msg==='string'?msg:JSON.stringify(msg));
  e.status=status;return e;
}
async function api(path,opts={}){
  const headers={...(opts.headers||{})};
  if(token)headers.Authorization='Bearer '+token;
  if(opts.body && !(opts.body instanceof FormData) && !headers['Content-Type'])headers['Content-Type']='application/json';
  const r=await fetch(API+path,{...opts,headers});
  let body=null;const ct=r.headers.get('content-type')||'';
  if(ct.includes('application/json')){try{body=await r.json()}catch{}}
  else {try{body=await r.text()}catch{}}
  if(!r.ok)throw appError(r.status,body);
  return body;
}
function fireTimestamp(v){
  const d=new Date(v);
  return {toDate:()=>new Date(d),toMillis:()=>d.getTime(),seconds:Math.floor(d.getTime()/1000),toJSON:()=>d.toISOString(),valueOf:()=>d.getTime()};
}
function wrap(v,k=''){
  if(Array.isArray(v))return v.map(x=>wrap(x));
  if(v&&typeof v==='object'){const o={};for(const [a,b] of Object.entries(v))o[a]=wrap(b,a);return o;}
  if(typeof v==='string'&&/At$/.test(k)&&/^\d{4}-\d{2}-\d{2}T/.test(v))return fireTimestamp(v);
  return v;
}
function notifyAuth(){for(const fn of listeners){try{fn(authUser)}catch(e){console.error(e)}}}
async function refreshAuth(){
  if(!token){authUser=null;notifyAuth();return null;}
  try{const me=await api('/auth/me');authUser={uid:String(me.id),email:me.email||'',displayName:me.name||'',...me};notifyAuth();return authUser;}
  catch(e){token='';localStorage.removeItem('a2_token');authUser=null;notifyAuth();return null;}
}

export function initializeApp(config,name='default'){return{config,name};}
export function getAuth(app){return{app,currentUser:app?.name==='creator'?(pendingCreator?.user||null):authUser};}
export function getFirestore(app){return{app};}
export function getMessaging(app){return{app};}
export async function isSupported(){return false;}
export async function getToken(){return null;}
export function onMessage(){return()=>{};}

export function onAuthStateChanged(auth,cb){listeners.add(cb);queueMicrotask(()=>refreshAuth().then(()=>cb(authUser)).catch(()=>cb(null)));return()=>listeners.delete(cb);}
export async function signInWithEmailAndPassword(auth,email,password){
  const r=await api('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
  token=r.access_token;localStorage.setItem('a2_token',token);
  authUser={uid:String(r.user.id),...r.user};notifyAuth();auth.currentUser=authUser;return{user:authUser};
}
export async function signOut(auth){
  if(auth?.app?.name==='creator'){pendingCreator=null;auth.currentUser=null;return;}
  token='';localStorage.removeItem('a2_token');authUser=null;auth.currentUser=null;notifyAuth();
}
export async function createUserWithEmailAndPassword(auth,email,password){
  if(auth?.app?.name!=='creator')throw new Error('Managed user creation is Admin-only');
  const uid='pending-'+crypto.randomUUID();pendingCreator={email,password,user:{uid,email}};auth.currentUser=pendingCreator.user;return{user:pendingCreator.user};
}
export async function sendPasswordResetEmail(){throw new Error('Password reset is managed by the A2 MESS HUB administrator.');}

export function collection(db,name){return{kind:'collection',name};}
export function doc(db,name,id){return{kind:'doc',name,id:String(id)};}
export function where(field,op,value){return{field,op,value};}
export function query(ref,...filters){return{...ref,filters};}
export function serverTimestamp(){return new Date().toISOString();}

class DocSnap{
  constructor(id,data,exists=true){this.id=String(id);this._data=wrap(data||{});this._exists=exists;}
  exists(){return this._exists;}
  data(){return this._data;}
}
class QuerySnap{constructor(rows){this.docs=(rows||[]).map(x=>new DocSnap(x.id||x.uid,x,true));}}

async function fetchRef(ref){
  if(ref.kind==='doc'){
    try{return new DocSnap(ref.id,await api('/live/doc/'+encodeURIComponent(ref.name)+'/'+encodeURIComponent(ref.id)),true)}
    catch(e){if(e.status===404)return new DocSnap(ref.id,{},false);throw e;}
  }
  let rows=await api('/live/collection/'+encodeURIComponent(ref.name));
  for(const f of ref.filters||[]){if(f.op==='==')rows=rows.filter(x=>String(x?.[f.field]??'')===String(f.value??''));}
  return new QuerySnap(rows);
}
export async function getDoc(ref){return fetchRef(ref);}
export async function getDocs(ref){return fetchRef(ref);}
export function onSnapshot(ref,cb,onerr){
  let stopped=false,last='';
  const run=async()=>{if(stopped)return;try{const snap=await fetchRef(ref);const sig=JSON.stringify(ref.kind==='doc'?snap.data():snap.docs.map(x=>x.data()));if(sig!==last){last=sig;cb(snap)}}catch(e){if(onerr)onerr(e);else console.error(e)}};
  run();const timer=setInterval(run,2500);return()=>{stopped=true;clearInterval(timer)};
}
function cleanPayload(v){
  if(v===undefined)return null;
  if(Array.isArray(v))return v.map(cleanPayload);
  if(v&&typeof v==='object'&&typeof v.toDate==='function')return v.toDate().toISOString();
  if(v&&typeof v==='object'){const o={};for(const[k,x]of Object.entries(v))o[k]=cleanPayload(x);return o;}
  return v;
}
async function createRecord(name,data){return api('/live/collection/'+encodeURIComponent(name),{method:'POST',body:JSON.stringify(cleanPayload(data))});}
async function updateRecord(name,id,data){return api('/live/doc/'+encodeURIComponent(name)+'/'+encodeURIComponent(id),{method:'PATCH',body:JSON.stringify(cleanPayload(data))});}
async function deleteRecord(name,id){return api('/live/doc/'+encodeURIComponent(name)+'/'+encodeURIComponent(id),{method:'DELETE'});}

export async function addDoc(ref,data){const r=await createRecord(ref.name,data);return{id:r.id};}
export async function updateDoc(ref,data){return updateRecord(ref.name,ref.id,data);}
export async function deleteDoc(ref){return deleteRecord(ref.name,ref.id);}
export async function setDoc(ref,data,options={}){
  const snap=await getDoc(ref);
  if(snap.exists())return updateRecord(ref.name,ref.id,data);
  if(ref.name==='mealSkips')return createRecord('mealSkips',{...data,_requestedId:ref.id});
  if(ref.name==='users'&&String(ref.id).startsWith('pending-')){
    if(!pendingCreator)throw new Error('Pending managed user credentials not found');
    const body={...cleanPayload(data),email:pendingCreator.email,password:pendingCreator.password};
    const r=await api('/live/users',{method:'POST',body:JSON.stringify(body)});pendingCreator.user={uid:r.id,email:pendingCreator.email};return r;
  }
  return createRecord(ref.name,data);
}
export function writeBatch(db){
  const ops=[];
  return{
    set:(ref,data,options)=>ops.push(['set',ref,data,options]),
    update:(ref,data)=>ops.push(['update',ref,data]),
    delete:(ref)=>ops.push(['delete',ref]),
    async commit(){for(const[kind,ref,data,options]of ops){if(kind==='set')await setDoc(ref,data,options);else if(kind==='update')await updateDoc(ref,data);else await deleteDoc(ref);}}
  };
}
window.__TECHMANZ_API__={api,refreshAuth,get token(){return token}};
