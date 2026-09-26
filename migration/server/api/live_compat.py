import calendar
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request


def create_live_compat_router(db, current_user, allow_roles):
    router = APIRouter(prefix="/live", tags=["live-compat"])

    def iso(v):
        return v.isoformat() if v is not None else None

    def month_date(value):
        if not value:
            today = date.today()
            return date(today.year, today.month, 1)
        try:
            y, m = map(int, str(value)[:7].split("-"))
            return date(y, m, 1)
        except Exception:
            raise HTTPException(422, "Month must use YYYY-MM")

    def uuid_value(value, label="id"):
        try:
            return uuid.UUID(str(value))
        except Exception:
            raise HTTPException(422, f"Invalid {label}")

    def require_role(user, *roles):
        if user["role"] not in roles:
            raise HTTPException(403, "Insufficient permission")

    def audit(cur, user_id, action, entity_type, entity_id, details=None):
        cur.execute(
            """
            INSERT INTO audit_log(user_id,action,entity_type,entity_id,details)
            VALUES(%s,%s,%s,%s,%s::jsonb)
            """,
            (user_id, action, entity_type, str(entity_id), json.dumps(details or {}, default=str)),
        )

    def linked_member_id(cur, user_id):
        cur.execute("SELECT id FROM members WHERE user_id=%s LIMIT 1", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def member_obj(cur, r):
        member_id = r[0]
        cur.execute(
            "SELECT billing_month,plan_amount FROM member_month_plans WHERE member_id=%s ORDER BY billing_month",
            (member_id,),
        )
        plans = {x[0].strftime("%Y-%m"): float(x[1]) for x in cur.fetchall()}
        cur.execute(
            "SELECT billing_month,amount FROM member_month_carry WHERE member_id=%s ORDER BY billing_month",
            (member_id,),
        )
        carries = {x[0].strftime("%Y-%m"): float(x[1]) for x in cur.fetchall()}
        return {
            "id": str(member_id),
            "uid": str(r[1]) if r[1] else "",
            "name": r[2],
            "email": r[3] or "",
            "phone": r[4] or "",
            "joinDate": iso(r[5]),
            "plan": f"AED {float(r[6]):g}",
            "planAmount": float(r[6]),
            "active": bool(r[7]),
            "currentBillingMonth": r[8] or "",
            "status": r[9] or "DUE",
            "paidAmount": float(r[10] or 0),
            "dueAmount": float(r[11] or 0),
            "advanceAmount": float(r[12] or 0),
            "planByMonth": plans,
            "manualCarryByMonth": carries,
            "createdAt": iso(r[13]),
            "updatedAt": iso(r[14]),
        }

    def all_members(cur, include_inactive=True):
        cur.execute(
            """
            SELECT id,user_id,name,email,phone,join_date,monthly_plan,active,
                   current_billing_month,status,paid_amount,due_amount,advance_amount,
                   created_at,updated_at
            FROM members
            WHERE (%s OR active=TRUE)
            ORDER BY lower(name),created_at
            """,
            (include_inactive,),
        )
        return [member_obj(cur, r) for r in cur.fetchall()]

    def inventory_rows(cur):
        cur.execute(
            """
            SELECT id,name,quantity,unit,minimum_quantity,active,created_at,updated_at
            FROM inventory WHERE active=TRUE ORDER BY lower(name),created_at
            """
        )
        return [
            {
                "id": str(r[0]), "name": r[1], "qty": float(r[2]), "unit": r[3] or "",
                "min": float(r[4]), "active": bool(r[5]), "createdAt": iso(r[6]), "updatedAt": iso(r[7])
            }
            for r in cur.fetchall()
        ]

    def meal_rows(cur):
        cur.execute("SELECT id,meal_date,slot,menu,created_at,updated_at FROM meals ORDER BY meal_date DESC,slot")
        return [
            {"id": str(r[0]), "date": iso(r[1]), "slot": r[2].title(), "menu": r[3] or "", "createdAt": iso(r[4]), "updatedAt": iso(r[5])}
            for r in cur.fetchall()
        ]

    def expense_rows(cur):
        cur.execute(
            """
            SELECT e.id,e.title,e.amount,e.category,e.expense_date,e.bill_path,e.bill_original_name,
                   e.created_by,e.created_at,e.updated_at,e.payment_method,e.created_by_name,
                   e.image_provider,e.legacy_bill_url,e.legacy_bill_file_id,u.name
            FROM expenses e LEFT JOIN users u ON u.id=e.created_by
            ORDER BY e.expense_date DESC,e.created_at DESC
            """
        )
        out=[]
        for r in cur.fetchall():
            bill_url = f"/api/expenses/{r[0]}/bill" if r[5] else (r[13] or "")
            out.append({
                "id": str(r[0]), "title": r[1], "amount": float(r[2]), "category": r[3] or "General",
                "expenseDate": iso(r[4]), "billUrl": bill_url, "billFileId": r[14] or "",
                "imageProvider": "local" if r[5] else (r[12] or ""), "createdBy": str(r[7]) if r[7] else "",
                "createdByName": r[11] or r[15] or "", "paymentMethod": r[10] or "CASH",
                "createdAt": iso(r[8]), "updatedAt": iso(r[9])
            })
        return out

    def payment_rows(cur, user):
        params=[]
        where=""
        if user["role"] == "member":
            mid=linked_member_id(cur,user["id"])
            if not mid:
                return []
            where="WHERE p.member_id=%s"
            params=[mid]
        elif user["role"] != "admin":
            return []
        cur.execute(
            f"""
            SELECT p.id,p.member_id,p.amount,p.payment_date,p.payment_method,p.status,p.reference,p.notes,
                   p.created_at,p.updated_at,p.billing_month,p.plan_amount,p.opening_carry,p.available_amount,
                   p.due_amount,p.advance_amount,p.display_name,p.display_phone,m.user_id,m.name,m.phone,m.monthly_plan
            FROM payments p LEFT JOIN members m ON m.id=p.member_id
            {where}
            ORDER BY p.created_at DESC
            """,
            params,
        )
        out=[]
        for r in cur.fetchall():
            bm=(r[10] or date(r[3].year,r[3].month,1)).strftime("%Y-%m")
            amount=float(r[2])
            out.append({
                "id":str(r[0]), "memberId":str(r[1]) if r[1] else "", "uid":str(r[18]) if r[18] else "",
                "name":r[16] or r[19] or "", "phone":r[17] or r[20] or "", "billingMonth":bm,
                "planAmount":float(r[11] if r[11] is not None else (r[21] or 0)), "paidAmount":amount, "amount":amount,
                "openingCarry":float(r[12] or 0), "availableAmount":float(r[13] if r[13] is not None else amount),
                "dueAmount":float(r[14] or 0), "advanceAmount":float(r[15] or 0), "status":str(r[5] or "paid").upper(),
                "paymentMethod":str(r[4] or "cash").upper().replace("BANK","ACCOUNT_TRANSFER"),
                "reference":r[6] or "", "notes":r[7] or "", "paymentDate":iso(r[3]),
                "createdAt":iso(r[8]), "updatedAt":iso(r[9])
            })
        return out

    def skip_rows(cur):
        cur.execute(
            """
            SELECT s.id,s.member_id,s.meal_date,s.slot,s.status,s.cutoff_at,s.created_at,s.updated_at,
                   m.user_id,m.name
            FROM meal_skips s JOIN members m ON m.id=s.member_id
            ORDER BY s.meal_date DESC,s.created_at DESC
            """
        )
        return [
            {"id":str(r[0]),"memberId":str(r[1]),"uid":str(r[8]) if r[8] else "","memberName":r[9],
             "date":iso(r[2]),"mealDate":iso(r[2]),"slot":r[3].title(),"status":str(r[4]).upper(),
             "cutoffAt":iso(r[5]),"createdAt":iso(r[6]),"updatedAt":iso(r[7])}
            for r in cur.fetchall()
        ]

    def closing_rows(cur):
        cur.execute(
            """
            SELECT id,billing_month,total_members,total_receivable,total_received,total_pending,total_expenses,
                   closing_balance,closed_at,created_at,member_snapshot,total_due_carry,total_advance_carry,total_weight
            FROM monthly_closings ORDER BY billing_month DESC
            """
        )
        return [
            {"id":r[1].strftime("%Y-%m"),"month":r[1].strftime("%Y-%m"),"status":"CLOSED",
             "memberCount":r[2],"totalReceivable":float(r[3]),"totalPaid":float(r[4]),"totalPending":float(r[5]),
             "totalExpense":float(r[6]),"closingBalance":float(r[7]),"closedAt":iso(r[8]),"createdAt":iso(r[9]),
             "members":r[10] or [],"totalDue":float(r[11] or 0),"totalAdvance":float(r[12] or 0),"totalWeight":float(r[13] or 0)}
            for r in cur.fetchall()
        ]

    def user_rows(cur):
        cur.execute("SELECT id,name,email,phone,role,active,created_at,updated_at FROM users ORDER BY lower(name)")
        out=[]
        for r in cur.fetchall():
            cur.execute("SELECT id FROM members WHERE user_id=%s LIMIT 1",(r[0],))
            m=cur.fetchone()
            out.append({"id":str(r[0]),"uid":str(r[0]),"name":r[1],"email":r[2] or "","phone":r[3] or "",
                        "role":r[4],"active":bool(r[5]),"memberId":str(m[0]) if m else "","createdAt":iso(r[6]),"updatedAt":iso(r[7])})
        return out

    @router.get("/state")
    def state(user=Depends(current_user)):
        with db() as conn:
            with conn.cursor() as cur:
                profile={"uid":str(user["id"]),"id":str(user["id"]),"name":user["name"],"email":user["email"] or "",
                         "phone":user["phone"] or "","role":user["role"],"active":bool(user["active"])}
                return {
                    "profile":profile,
                    "config":{"initialized":True,"imageProvider":"local","runtime":"techmanz"},
                    "members":all_members(cur,True),
                    "inventory":inventory_rows(cur),
                    "meals":meal_rows(cur),
                    "expenses":expense_rows(cur),
                    "payments":payment_rows(cur,user),
                    "users":user_rows(cur) if user["role"]=="admin" else [],
                    "monthlyClosings":closing_rows(cur) if user["role"]=="admin" else [],
                    "mealSkips":skip_rows(cur),
                }

    @router.get("/collection/{collection}")
    def collection(collection:str,user=Depends(current_user)):
        s=state(user)
        key={"mealSkips":"mealSkips","monthlyClosings":"monthlyClosings"}.get(collection,collection)
        if key not in s:
            raise HTTPException(404,"Unsupported collection")
        return s[key]

    @router.get("/doc/{collection}/{doc_id}")
    def document(collection:str,doc_id:str,user=Depends(current_user)):
        if collection=="system" and doc_id=="config":
            return {"initialized":True,"imageProvider":"local","runtime":"techmanz"}
        s=state(user)
        rows=s.get(collection)
        if rows is None:
            raise HTTPException(404,"Unsupported collection")
        for row in rows:
            if str(row.get("id"))==doc_id or str(row.get("uid"))==doc_id:
                return row
        raise HTTPException(404,"Document not found")

    @router.post("/collection/{collection}")
    async def create_doc(collection:str,request:Request,user=Depends(current_user)):
        body=await request.json()
        now=date.today()
        with db() as conn:
            with conn.cursor() as cur:
                new_id=uuid.uuid4()
                if collection=="members":
                    require_role(user,"admin")
                    plan=float(body.get("planAmount") or str(body.get("plan") or "0").replace("AED","").strip() or 0)
                    join=body.get("joinDate") or now.isoformat()
                    cur.execute("""INSERT INTO members(id,name,email,phone,join_date,monthly_plan,active,current_billing_month,status,paid_amount,due_amount,advance_amount)
                                 VALUES(%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s)""",
                                (new_id,body.get("name") or "Member",body.get("email") or None,body.get("phone") or None,join,plan,
                                 body.get("currentBillingMonth"),body.get("status") or "DUE",body.get("paidAmount") or 0,body.get("dueAmount") or plan,body.get("advanceAmount") or 0))
                elif collection=="payments":
                    require_role(user,"admin")
                    member_id=uuid_value(body.get("memberId") or body.get("uid"),"member id")
                    bm=month_date(body.get("billingMonth"))
                    amount=float(body.get("paidAmount") or body.get("amount") or 0)
                    if amount<=0: raise HTTPException(422,"Payment amount must be greater than zero")
                    method=str(body.get("paymentMethod") or "CASH").upper()
                    dbmethod={"CASH":"cash","ACCOUNT_TRANSFER":"bank","CARD":"card"}.get(method,"other")
                    cur.execute("""INSERT INTO payments(id,member_id,amount,payment_date,payment_method,status,reference,notes,created_by,billing_month,plan_amount,opening_carry,available_amount,due_amount,advance_amount,display_name,display_phone)
                                 VALUES(%s,%s,%s,%s,%s,'paid',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (new_id,member_id,amount,body.get("paymentDate") or now,dbmethod,body.get("reference") or "",body.get("notes") or "",user["id"],bm,
                                 body.get("planAmount"),body.get("openingCarry") or 0,body.get("availableAmount"),body.get("dueAmount") or 0,body.get("advanceAmount") or 0,
                                 body.get("name") or "",body.get("phone") or ""))
                elif collection=="meals":
                    require_role(user,"admin","chef")
                    cur.execute("INSERT INTO meals(id,meal_date,slot,menu,created_by) VALUES(%s,%s,%s,%s,%s)",
                                (new_id,body.get("date") or body.get("mealDate") or now,str(body.get("slot") or "").lower(),body.get("menu") or "",user["id"]))
                elif collection=="inventory":
                    require_role(user,"admin","chef")
                    cur.execute("INSERT INTO inventory(id,name,quantity,unit,minimum_quantity,active) VALUES(%s,%s,%s,%s,%s,TRUE)",
                                (new_id,body.get("name") or "Item",body.get("qty") or 0,body.get("unit") or None,body.get("min") or 0))
                elif collection=="expenses":
                    require_role(user,"admin","chef")
                    cur.execute("""INSERT INTO expenses(id,title,amount,category,expense_date,created_by,payment_method,created_by_name,image_provider,legacy_bill_url,legacy_bill_file_id)
                                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (new_id,body.get("title") or "Expense",body.get("amount") or 0,body.get("category") or None,body.get("expenseDate") or now,user["id"],
                                 body.get("paymentMethod") or "CASH",user["name"],body.get("imageProvider") or None,body.get("billUrl") or None,body.get("billFileId") or None))
                else:
                    raise HTTPException(404,"Unsupported create collection")
                audit(cur,user["id"],"live_create",collection,new_id,body)
            conn.commit()
        return {"id":str(new_id)}

    @router.patch("/doc/{collection}/{doc_id}")
    async def update_doc(collection:str,doc_id:str,request:Request,user=Depends(current_user)):
        body=await request.json()
        obj_id=uuid_value(doc_id)
        with db() as conn:
            with conn.cursor() as cur:
                if collection=="members":
                    require_role(user,"admin")
                    for key,value in body.items():
                        if key.startswith("planByMonth."):
                            m=month_date(key.split(".",1)[1])
                            cur.execute("""INSERT INTO member_month_plans(id,member_id,billing_month,plan_amount,created_by)
                                         VALUES(%s,%s,%s,%s,%s) ON CONFLICT(member_id,billing_month) DO UPDATE SET plan_amount=EXCLUDED.plan_amount,updated_at=now()""",
                                        (uuid.uuid4(),obj_id,m,float(value),user["id"]))
                        elif key.startswith("manualCarryByMonth."):
                            m=month_date(key.split(".",1)[1])
                            cur.execute("""INSERT INTO member_month_carry(id,member_id,billing_month,amount,source,created_by)
                                         VALUES(%s,%s,%s,%s,'manual',%s) ON CONFLICT(member_id,billing_month) DO UPDATE SET amount=EXCLUDED.amount,source='manual',updated_at=now()""",
                                        (uuid.uuid4(),obj_id,m,float(value),user["id"]))
                    fields={"name":"name","email":"email","phone":"phone","joinDate":"join_date","planAmount":"monthly_plan","active":"active",
                            "currentBillingMonth":"current_billing_month","status":"status","paidAmount":"paid_amount","dueAmount":"due_amount","advanceAmount":"advance_amount"}
                    sets=[]; vals=[]
                    for k,col in fields.items():
                        if k in body: sets.append(f"{col}=%s"); vals.append(body[k])
                    if "plan" in body and "planAmount" not in body:
                        try: sets.append("monthly_plan=%s"); vals.append(float(str(body["plan"]).replace("AED","").strip()))
                        except Exception: pass
                    if sets:
                        vals += [obj_id]
                        cur.execute(f"UPDATE members SET {','.join(sets)},updated_at=now() WHERE id=%s",vals)
                elif collection=="payments":
                    require_role(user,"admin")
                    fields={"amount":"amount","paidAmount":"amount","billingMonth":"billing_month","planAmount":"plan_amount","openingCarry":"opening_carry",
                            "availableAmount":"available_amount","dueAmount":"due_amount","advanceAmount":"advance_amount","name":"display_name","phone":"display_phone",
                            "reference":"reference","notes":"notes"}
                    sets=[];vals=[]
                    for k,col in fields.items():
                        if k in body:
                            val=month_date(body[k]) if k=="billingMonth" else body[k]
                            sets.append(f"{col}=%s"); vals.append(val)
                    if "paymentMethod" in body:
                        method=str(body["paymentMethod"]).upper(); sets.append("payment_method=%s"); vals.append({"CASH":"cash","ACCOUNT_TRANSFER":"bank","CARD":"card"}.get(method,"other"))
                    if sets: vals.append(obj_id);cur.execute(f"UPDATE payments SET {','.join(sets)},updated_at=now() WHERE id=%s",vals)
                elif collection=="meals":
                    require_role(user,"admin","chef")
                    fields={"date":"meal_date","mealDate":"meal_date","slot":"slot","menu":"menu"};sets=[];vals=[]
                    for k,col in fields.items():
                        if k in body: sets.append(f"{col}=%s");vals.append(str(body[k]).lower() if k=="slot" else body[k])
                    if sets: vals.append(obj_id);cur.execute(f"UPDATE meals SET {','.join(sets)},updated_at=now() WHERE id=%s",vals)
                elif collection=="inventory":
                    require_role(user,"admin","chef")
                    fields={"name":"name","qty":"quantity","unit":"unit","min":"minimum_quantity","active":"active"};sets=[];vals=[]
                    for k,col in fields.items():
                        if k in body: sets.append(f"{col}=%s");vals.append(body[k])
                    if sets: vals.append(obj_id);cur.execute(f"UPDATE inventory SET {','.join(sets)},updated_at=now() WHERE id=%s",vals)
                elif collection=="expenses":
                    require_role(user,"admin")
                    fields={"title":"title","amount":"amount","category":"category","expenseDate":"expense_date","paymentMethod":"payment_method",
                            "billUrl":"legacy_bill_url","billFileId":"legacy_bill_file_id","imageProvider":"image_provider"};sets=[];vals=[]
                    for k,col in fields.items():
                        if k in body: sets.append(f"{col}=%s");vals.append(body[k])
                    if sets: vals.append(obj_id);cur.execute(f"UPDATE expenses SET {','.join(sets)},updated_at=now() WHERE id=%s",vals)
                elif collection=="users":
                    require_role(user,"admin")
                    fields={"name":"name","phone":"phone","role":"role","active":"active"};sets=[];vals=[]
                    for k,col in fields.items():
                        if k in body: sets.append(f"{col}=%s");vals.append(body[k])
                    if sets: vals.append(obj_id);cur.execute(f"UPDATE users SET {','.join(sets)},updated_at=now() WHERE id=%s",vals)
                    if "memberId" in body:
                        cur.execute("UPDATE members SET user_id=NULL WHERE user_id=%s",(obj_id,))
                        if body["memberId"]:
                            cur.execute("UPDATE members SET user_id=%s,updated_at=now() WHERE id=%s",(obj_id,uuid_value(body["memberId"],"member id")))
                else:
                    raise HTTPException(404,"Unsupported update collection")
                audit(cur,user["id"],"live_update",collection,obj_id,body)
            conn.commit()
        return {"id":doc_id,"updated":True}

    @router.delete("/doc/{collection}/{doc_id}")
    def delete_doc(collection:str,doc_id:str,user=Depends(current_user)):
        obj_id=uuid_value(doc_id)
        table={"members":"members","payments":"payments","meals":"meals","inventory":"inventory","expenses":"expenses"}.get(collection)
        if not table: raise HTTPException(404,"Unsupported delete collection")
        require_role(user,"admin")
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {table} WHERE id=%s",(obj_id,))
                audit(cur,user["id"],"live_delete",collection,obj_id,{})
            conn.commit()
        return {"id":doc_id,"deleted":True}

    @router.put("/members/{member_id}/month-plan/{billing_month}")
    async def set_month_plan(member_id:str,billing_month:str,request:Request,user=Depends(current_user)):
        require_role(user,"admin")
        body=await request.json(); amount=float(body.get("planAmount") or body.get("amount") or 0)
        if amount not in {100.0,200.0,250.0}: raise HTTPException(422,"Plan must be AED 100, 200 or 250")
        mid=uuid_value(member_id,"member id"); m=month_date(billing_month)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO member_month_plans(id,member_id,billing_month,plan_amount,created_by)
                             VALUES(%s,%s,%s,%s,%s) ON CONFLICT(member_id,billing_month) DO UPDATE SET plan_amount=EXCLUDED.plan_amount,updated_at=now()""",
                            (uuid.uuid4(),mid,m,amount,user["id"]))
            conn.commit()
        return {"memberId":member_id,"billingMonth":billing_month,"planAmount":amount}

    @router.put("/members/{member_id}/carry/{billing_month}")
    async def set_carry(member_id:str,billing_month:str,request:Request,user=Depends(current_user)):
        require_role(user,"admin")
        body=await request.json(); amount=float(body.get("amount") or 0);mid=uuid_value(member_id,"member id");m=month_date(billing_month)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO member_month_carry(id,member_id,billing_month,amount,source,created_by)
                             VALUES(%s,%s,%s,%s,'manual',%s) ON CONFLICT(member_id,billing_month) DO UPDATE SET amount=EXCLUDED.amount,source='manual',updated_at=now()""",
                            (uuid.uuid4(),mid,m,amount,user["id"]))
            conn.commit()
        return {"memberId":member_id,"billingMonth":billing_month,"amount":amount}

    return router
