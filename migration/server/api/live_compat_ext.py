import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse


def create_live_compat_ext_router(db, current_user):
    router=APIRouter(prefix="/live",tags=["live-compat-ext"])
    bill_root=Path("/data/bills").resolve()
    bill_root.mkdir(parents=True,exist_ok=True)

    def need(user,*roles):
        if user["role"] not in roles:
            raise HTTPException(403,"Insufficient permission")

    def as_uuid(value,label="id"):
        try:return uuid.UUID(str(value))
        except Exception:raise HTTPException(422,f"Invalid {label}")

    def linked_member(cur,user_id):
        cur.execute("SELECT id FROM members WHERE user_id=%s LIMIT 1",(user_id,))
        r=cur.fetchone()
        return r[0] if r else None

    def password_hash(password):
        salt=secrets.token_bytes(16)
        d=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,600000)
        return "pbkdf2_sha256$600000$"+salt.hex()+"$"+d.hex()

    def audit(cur,user_id,action,entity_type,entity_id,details=None):
        cur.execute(
            "INSERT INTO audit_log(user_id,action,entity_type,entity_id,details) VALUES(%s,%s,%s,%s,%s::jsonb)",
            (user_id,action,entity_type,str(entity_id),json.dumps(details or {},default=str))
        )

    @router.post("/users")
    async def create_user(request:Request,user=Depends(current_user)):
        need(user,"admin")
        b=await request.json()
        role=str(b.get("role") or "").lower()
        email=str(b.get("email") or "").strip().lower()
        password=str(b.get("password") or "")
        name=str(b.get("name") or "").strip()
        member_id=str(b.get("memberId") or "")
        if role not in {"chef","member"}:
            raise HTTPException(422,"Role must be chef or member")
        if not name or "@" not in email or len(password)<6:
            raise HTTPException(422,"Valid name, email and password are required")
        if role=="member" and not member_id:
            raise HTTPException(422,"Select a member to link")
        uid=uuid.uuid4()
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE lower(email)=lower(%s)",(email,))
                if cur.fetchone():
                    raise HTTPException(409,"Email already exists")
                cur.execute(
                    "INSERT INTO users(id,name,email,phone,role,active,password_hash) VALUES(%s,%s,%s,%s,%s,TRUE,%s)",
                    (uid,name,email,str(b.get("phone") or ""),role,password_hash(password))
                )
                if role=="member":
                    mid=as_uuid(member_id,"member id")
                    cur.execute(
                        "UPDATE members SET user_id=%s,email=%s,updated_at=now() WHERE id=%s RETURNING id",
                        (uid,email,mid)
                    )
                    if not cur.fetchone():
                        raise HTTPException(404,"Member not found")
                audit(cur,user["id"],"LIVE_USER_CREATED","user",uid,{"role":role,"email":email,"memberId":member_id})
            conn.commit()
        return {"id":str(uid),"uid":str(uid),"role":role,"memberId":member_id}

    @router.post("/bill-upload")
    async def upload_bill(bill:UploadFile=File(...),user=Depends(current_user)):
        need(user,"admin","chef")
        ext={"image/jpeg":".jpg","image/png":".png","application/pdf":".pdf"}.get((bill.content_type or "").lower())
        if not ext:
            raise HTTPException(415,"Bill must be JPG, PNG or PDF")
        data=await bill.read(10*1024*1024+1)
        if len(data)>10*1024*1024:
            raise HTTPException(413,"Bill is larger than 10 MB")
        name="live-"+uuid.uuid4().hex+ext
        target=(bill_root/name).resolve()
        if bill_root not in target.parents:
            raise HTTPException(400,"Invalid bill path")
        target.write_bytes(data)
        return {"billUrl":f"/api/live/bill-public/{name}","billFileId":name,"imageProvider":"local"}

    @router.get("/bill-public/{file_id}")
    def read_bill(file_id:str):
        name=Path(file_id).name
        if name!=file_id or not name.startswith("live-"):
            raise HTTPException(404,"Bill not found")
        target=(bill_root/name).resolve()
        if bill_root not in target.parents or not target.is_file():
            raise HTTPException(404,"Bill not found")
        return FileResponse(target)

    @router.post("/collection/mealSkips")
    async def create_skip(request:Request,user=Depends(current_user)):
        need(user,"member")
        b=await request.json()
        meal_date=b.get("date") or b.get("mealDate")
        slot=str(b.get("meal") or b.get("slot") or "").lower()
        cutoff=b.get("cutoffAt")
        if not meal_date or slot not in {"breakfast","lunch","dinner"}:
            raise HTTPException(422,"Valid meal date and slot are required")
        cutoff_dt=None
        if cutoff:
            try:
                cutoff_dt=datetime.fromisoformat(str(cutoff).replace("Z","+00:00"))
                if cutoff_dt.tzinfo is None:
                    cutoff_dt=cutoff_dt.replace(tzinfo=timezone.utc)
            except Exception:
                raise HTTPException(422,"Invalid cutoff")
            if datetime.now(timezone.utc)>=cutoff_dt:
                raise HTTPException(409,"Skip cutoff has passed")
        with db() as conn:
            with conn.cursor() as cur:
                mid=linked_member(cur,user["id"])
                if not mid:
                    raise HTTPException(409,"Member profile not linked")
                sid=uuid.uuid4()
                cur.execute(
                    """INSERT INTO meal_skips(id,member_id,meal_date,slot,status,cutoff_at)
                       VALUES(%s,%s,%s,%s,'skipped',%s)
                       ON CONFLICT(member_id,meal_date,slot)
                       DO UPDATE SET status='skipped',cutoff_at=EXCLUDED.cutoff_at,updated_at=now()
                       RETURNING id""",
                    (sid,mid,meal_date,slot,cutoff_dt)
                )
                sid=cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO notifications(id,type,recipient_member_id,channel,title,message,status)
                       VALUES(%s,'meal_skip',NULL,'in_app','Meal Skip',%s,'pending')""",
                    (uuid.uuid4(),f"{user['name']} skipped {slot.title()} on {meal_date}")
                )
                audit(cur,user["id"],"MEAL_SKIPPED","meal_skip",sid,{"meal_date":meal_date,"slot":slot})
            conn.commit()
        return {"id":str(sid)}

    @router.delete("/doc/mealSkips/{skip_id}")
    def delete_skip(skip_id:str,user=Depends(current_user)):
        sid=as_uuid(skip_id,"skip id")
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT member_id,cutoff_at FROM meal_skips WHERE id=%s",(sid,))
                r=cur.fetchone()
                if not r:
                    raise HTTPException(404,"Meal skip not found")
                if user["role"]!="admin":
                    need(user,"member")
                    mid=linked_member(cur,user["id"])
                    if not mid or mid!=r[0]:
                        raise HTTPException(403,"Cannot remove another member's skip")
                    if r[1] and datetime.now(timezone.utc)>=r[1]:
                        raise HTTPException(409,"Skip cutoff has passed")
                cur.execute("DELETE FROM meal_skips WHERE id=%s",(sid,))
                audit(cur,user["id"],"MEAL_SKIP_REMOVED","meal_skip",sid,{})
            conn.commit()
        return {"id":skip_id,"deleted":True}

    @router.delete("/doc/users/{user_id}")
    def delete_user(user_id:str,user=Depends(current_user)):
        need(user,"admin")
        uid=as_uuid(user_id,"user id")
        if uid==user["id"]:
            raise HTTPException(400,"Cannot remove your own administrator account")
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE members SET user_id=NULL,updated_at=now() WHERE user_id=%s",(uid,))
                cur.execute("DELETE FROM users WHERE id=%s RETURNING id",(uid,))
                if not cur.fetchone():
                    raise HTTPException(404,"User not found")
                audit(cur,user["id"],"LIVE_USER_REMOVED","user",uid,{})
            conn.commit()
        return {"id":user_id,"deleted":True}

    return router
