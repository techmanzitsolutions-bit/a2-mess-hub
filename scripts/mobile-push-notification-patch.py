from pathlib import Path
root=Path('/tmp/a2-pwa/www'); app=root/'app.html'; sw=root/'sw.js'; s=app.read_text()
vapid='BFVCiPfoRZ6iDh2FXCfyZHZqyjDxVXyKl4zxffSQ3iuiCzVFlVVZGj1let29ub8sKUzQsbZKT9Bddno4HZbpFTA'
# Add Messaging SDK to the existing module.
needle="import{getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch,query,where}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-firestore.js';"
if needle not in s:
    needle="import{getFirestore,doc,getDoc,setDoc,collection,onSnapshot,addDoc,updateDoc,deleteDoc,serverTimestamp,writeBatch}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-firestore.js';"
if "firebase-messaging.js" not in s:
    s=s.replace(needle,needle+"\nimport{getMessaging,getToken,onMessage,isSupported}from'https://www.gstatic.com/firebasejs/11.9.1/firebase-messaging.js';")
# Push permission/token registration. Public VAPID key is intentionally client-visible.
insert="""
const A2_PUSH_VAPID='"""+vapid+"""';
async function enableA2MobilePush(){
 try{
  if(!('Notification'in window)||!('serviceWorker'in navigator)||!(await isSupported()))return toast('Push notifications are not supported on this device/browser');
  const permission=await Notification.requestPermission();
  if(permission!=='granted')return toast('Notification permission was not allowed');
  const reg=await navigator.serviceWorker.ready;
  const messaging=getMessaging(fb);
  const token=await getToken(messaging,{vapidKey:A2_PUSH_VAPID,serviceWorkerRegistration:reg});
  if(!token)throw new Error('Firebase did not return a notification token');
  const uid=auth.currentUser?.uid;if(!uid)throw new Error('Please login first');
  await setDoc(doc(db,'pushTokens',uid),{uid,token,role:state.profile?.role||'',active:true,platform:navigator.userAgent,updatedAt:serverTimestamp()},{merge:true});
  localStorage.setItem('a2_push_enabled','1');toast('Mobile notifications enabled ✅');
 }catch(e){err(e)}
}
window.enableA2MobilePush=enableA2MobilePush;
function installA2PushButton(){if(!state.profile)return;setTimeout(()=>{if(document.getElementById('a2PushEnable'))return;const host=document.querySelector('.top');if(!host)return;const b=document.createElement('button');b.id='a2PushEnable';b.className='ghost';b.textContent=Notification.permission==='granted'?'🔔 Notifications ON':'🔔 Enable Notifications';b.onclick=enableA2MobilePush;host.appendChild(b)},100)}
try{isSupported().then(ok=>{if(!ok)return;const messaging=getMessaging(fb);onMessage(messaging,p=>{const n=p.notification||{},d=p.data||{};if(Notification.permission==='granted')new Notification(n.title||d.title||'A2 MESS HUB',{body:n.body||d.body||'New update',icon:'./logo.svg',tag:d.tag||'a2-live'});toast((n.title||d.title||'New notification')+(n.body||d.body?' · '+(n.body||d.body):''))})})}catch(e){console.warn('A2 push foreground setup',e)}
"""
anchor="const state={profile:null,page:'dashboard'"
if 'A2_PUSH_VAPID' not in s and anchor in s:
    pos=s.index(anchor); line_end=s.index('\n',pos); s=s[:line_end+1]+insert+s[line_end+1:]
# Ensure button appears after dynamic renders without altering existing render logic.
if 'a2PushRenderObserver' not in s:
    s=s.replace('</body>',"<script id=\"a2PushRenderObserver\">new MutationObserver(()=>{if(window.installA2PushButton)window.installA2PushButton()}).observe(document.getElementById('app'),{childList:true,subtree:true});</script></body>")
# Expose installer globally after definition.
s=s.replace('function installA2PushButton(){','window.installA2PushButton=function installA2PushButton(){')
app.write_text(s)
# Add Firebase Messaging background handler to generated service worker.
t=sw.read_text()
if 'firebase-messaging-sw' not in t:
    t += """
// firebase-messaging-sw: A2 MESS HUB background mobile notifications
importScripts('https://www.gstatic.com/firebasejs/11.9.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.9.1/firebase-messaging-compat.js');
firebase.initializeApp({apiKey:'AIzaSyDOUJGSLfDrmmc74YUGRkDU1b4P2gYmGyU',authDomain:'a2-mess-hub.firebaseapp.com',projectId:'a2-mess-hub',storageBucket:'a2-mess-hub.firebasestorage.app',messagingSenderId:'451214844236',appId:'1:451214844236:android:546b7783ecf04e40af6fe9'});
const a2Messaging=firebase.messaging();
a2Messaging.onBackgroundMessage(payload=>{const n=payload.notification||{},d=payload.data||{};return self.registration.showNotification(n.title||d.title||'A2 MESS HUB',{body:n.body||d.body||'New update',icon:'./logo.svg',badge:'./logo.svg',data:{url:d.url||'./'},tag:d.tag||'a2-mess-hub'})});
self.addEventListener('notificationclick',event=>{event.notification.close();event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(ws=>{for(const w of ws){if('focus'in w)return w.focus()}return clients.openWindow(event.notification.data?.url||'./')}))});
"""
sw.write_text(t)
print('Added Firebase Web Push permission, token registration and background service worker')
