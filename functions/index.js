const {onCall,HttpsError}=require('firebase-functions/v2/https');
const {onDocumentCreated}=require('firebase-functions/v2/firestore');
const {defineSecret}=require('firebase-functions/params');
const admin=require('firebase-admin');
admin.initializeApp();
const db=admin.firestore();

async function requireAdmin(auth){
  if(!auth) throw new HttpsError('unauthenticated','Login required');
  const snap=await db.collection('users').doc(auth.uid).get();
  const profile=snap.data();
  if(!snap.exists||profile.role!=='admin'||profile.active===false||profile.removed===true) throw new HttpsError('permission-denied','Active Admin only');
  return profile;
}

exports.createManagedUser=onCall(async req=>{
  await requireAdmin(req.auth);
  const {email,password,name,role,memberId=''}=req.data||{};
  const normalizedEmail=String(email||'').trim().toLowerCase();
  if(!normalizedEmail||!password||password.length<8||!name||!['chef','member'].includes(role)) throw new HttpsError('invalid-argument','Valid name, email, password (8+) and chef/member role required');
  let member=null;
  if(role==='member'){
    if(!memberId) throw new HttpsError('invalid-argument','Member link required');
    const ms=await db.collection('members').doc(memberId).get();
    if(!ms.exists) throw new HttpsError('not-found','Member record not found');
    member=ms.data();
    if(String(member.uid||'').trim()) throw new HttpsError('already-exists','This member is already linked to a login');
  }
  let user;
  try{
    user=await admin.auth().createUser({email:normalizedEmail,password,displayName:name,disabled:false});
    const batch=db.batch();
    batch.set(db.collection('users').doc(user.uid),{uid:user.uid,name,email:normalizedEmail,role,memberId:role==='member'?memberId:'',active:true,removed:false,createdBy:req.auth.uid,createdAt:admin.firestore.FieldValue.serverTimestamp()});
    if(role==='member') batch.set(db.collection('members').doc(memberId),{uid:user.uid,loginEmail:normalizedEmail,updatedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
    await batch.commit();
    return {uid:user.uid};
  }catch(e){
    if(user?.uid) await admin.auth().deleteUser(user.uid).catch(()=>{});
    if(e.code==='auth/email-already-exists') throw new HttpsError('already-exists','This email already has a Firebase login');
    if(e instanceof HttpsError) throw e;
    throw new HttpsError('internal',e.message||'User creation failed');
  }
});

exports.updateManagedUser=onCall(async req=>{
  await requireAdmin(req.auth);
  const {uid,name,role,disabled,memberId}=req.data||{};
  if(!uid) throw new HttpsError('invalid-argument','uid required');
  if(role&&!['chef','member'].includes(role)) throw new HttpsError('invalid-argument','Only chef/member roles are assignable');
  const ref=db.collection('users').doc(uid),snap=await ref.get();
  if(!snap.exists) throw new HttpsError('not-found','User profile not found');
  const old=snap.data(),patch={updatedAt:admin.firestore.FieldValue.serverTimestamp()};
  if(memberId){
    const memberSnap=await db.collection('members').doc(memberId).get();
    if(!memberSnap.exists) throw new HttpsError('not-found','Member record not found');
    const linkedUid=String(memberSnap.data().uid||'').trim();
    if(linkedUid&&linkedUid!==uid) throw new HttpsError('already-exists','This member is already linked to another login');
  }
  if(name)patch.name=name;
  if(role)patch.role=role;
  if(memberId!==undefined)patch.memberId=memberId||'';
  if(typeof disabled==='boolean'){patch.active=!disabled;patch.removed=false;}
  await admin.auth().updateUser(uid,{...(name?{displayName:name}:{}),...(typeof disabled==='boolean'?{disabled}:{})});
  const batch=db.batch();batch.set(ref,patch,{merge:true});
  if(old.memberId&&memberId!==undefined&&old.memberId!==memberId)batch.set(db.collection('members').doc(old.memberId),{uid:'',loginEmail:'',updatedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
  const target=memberId!==undefined?memberId:old.memberId;
  if(target)batch.set(db.collection('members').doc(target),{uid,updatedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
  await batch.commit();
  return {ok:true};
});

exports.deleteManagedUser=onCall(async req=>{
  await requireAdmin(req.auth);
  const {uid}=req.data||{};
  if(!uid||uid===req.auth.uid) throw new HttpsError('invalid-argument','A different user uid is required');
  const ref=db.collection('users').doc(uid),snap=await ref.get(),profile=snap.data()||{};
  await admin.auth().deleteUser(uid).catch(e=>{if(e.code!=='auth/user-not-found')throw e});
  const batch=db.batch();
  batch.delete(ref);
  if(profile.memberId)batch.set(db.collection('members').doc(profile.memberId),{uid:'',loginEmail:'',updatedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
  batch.set(db.collection('deletedUsers').doc(uid),{uid,email:profile.email||'',name:profile.name||'',deletedBy:req.auth.uid,deletedAt:admin.firestore.FieldValue.serverTimestamp()});
  await batch.commit();
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

exports.queueDueReminder=onDocumentCreated('notifications/{id}',async e=>e.data.ref.set({serverReceivedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true}));
