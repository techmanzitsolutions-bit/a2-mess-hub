const {onCall,HttpsError}=require('firebase-functions/v2/https');
const {onDocumentCreated}=require('firebase-functions/v2/firestore');
const {defineSecret}=require('firebase-functions/params');
const admin=require('firebase-admin');
admin.initializeApp();
const db=admin.firestore();

async function requireAdmin(auth){
  if(!auth) throw new HttpsError('unauthenticated','Login required');
  const snap=await db.collection('users').doc(auth.uid).get();
  if(!snap.exists || snap.data().role!=='admin') throw new HttpsError('permission-denied','Admin only');
}

exports.createManagedUser=onCall(async req=>{
  await requireAdmin(req.auth);
  const {email,password,name,role,phone='',plan=''}=req.data||{};
  if(!email||!password||!name||!['chef','member'].includes(role)) throw new HttpsError('invalid-argument','Valid name, email, password and chef/member role required');
  const user=await admin.auth().createUser({email,password,displayName:name,disabled:false});
  await db.collection('users').doc(user.uid).set({name,email,phone,plan,role,active:true,createdAt:admin.firestore.FieldValue.serverTimestamp()});
  if(role==='member') await db.collection('members').doc(user.uid).set({uid:user.uid,name,email,phone,plan,status:'DUE',active:true,createdAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
  return {uid:user.uid};
});

exports.updateManagedUser=onCall(async req=>{
  await requireAdmin(req.auth);
  const {uid,role,disabled,name}=req.data||{};
  if(!uid) throw new HttpsError('invalid-argument','uid required');
  if(role && !['chef','member'].includes(role)) throw new HttpsError('invalid-argument','Only chef/member roles are assignable');
  const patch={}; if(role)patch.role=role;if(name)patch.name=name;if(typeof disabled==='boolean')patch.active=!disabled;
  await db.collection('users').doc(uid).set(patch,{merge:true});
  const authPatch={};if(name)authPatch.displayName=name;if(typeof disabled==='boolean')authPatch.disabled=disabled;
  if(Object.keys(authPatch).length)await admin.auth().updateUser(uid,authPatch);
  return {ok:true};
});

exports.resetManagedUserPassword=onCall(async req=>{
  await requireAdmin(req.auth);
  const {uid,password}=req.data||{};
  if(!uid||!password||password.length<8) throw new HttpsError('invalid-argument','uid and password (8+ chars) required');
  await admin.auth().updateUser(uid,{password});
  return {ok:true};
});

const whatsappToken=defineSecret('WHATSAPP_TOKEN');
const whatsappPhoneId=defineSecret('WHATSAPP_PHONE_NUMBER_ID');
exports.sendWhatsApp=onCall({secrets:[whatsappToken,whatsappPhoneId]},async req=>{
  await requireAdmin(req.auth);
  const {to,template='payment_reminder',language='en_US'}=req.data||{};
  if(!to) throw new HttpsError('invalid-argument','Phone number required');
  const r=await fetch(`https://graph.facebook.com/v23.0/${whatsappPhoneId.value()}/messages`,{method:'POST',headers:{Authorization:`Bearer ${whatsappToken.value()}`,'Content-Type':'application/json'},body:JSON.stringify({messaging_product:'whatsapp',to,type:'template',template:{name:template,language:{code:language}}})});
  const body=await r.json();
  if(!r.ok) throw new HttpsError('internal',body?.error?.message||'WhatsApp send failed');
  return body;
});

exports.queueDueReminder=onDocumentCreated('notifications/{id}',async e=>{
  // Reserved automation hook. Actual WhatsApp sending is intentionally performed
  // through sendWhatsApp after Meta credentials/templates are configured.
  return e.data.ref.set({serverReceivedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
});
