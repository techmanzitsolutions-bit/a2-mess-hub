import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field


ALLOWED_COLLECTIONS = {
    "system", "users", "members", "inventory", "meals", "mealSkips",
    "expenses", "payments", "monthlyClosings", "settings", "notifications",
    "pushTokens",
}

MEMBER_READABLE = {"system", "members", "inventory", "meals", "mealSkips", "expenses", "payments", "settings"}
CHEF_READABLE = {"system", "members", "inventory", "meals", "mealSkips", "expenses", "settings"}
ADMIN_READABLE = ALLOWED_COLLECTIONS


class CompatCreateUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: str = Field(default="", max_length=120)


class CompatResetPassword(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class BatchRequest(BaseModel):
    operations: list[dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_server_timestamps(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__server_timestamp__") is True and len(value) == 1:
            return _now_iso()
        return {k: _resolve_server_timestamps(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_server_timestamps(v) for v in value]
    return value


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base or {})
    for key, value in (patch or {}).items():
        if "." in key:
            _deep_set(out, key, value)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _deep_set(target: dict[str, Any], path: str, value: Any) -> None:
    bits = path.split(".")
    cur = target
    for bit in bits[:-1]:
        nxt = cur.get(bit)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[bit] = nxt
        cur = nxt
    cur[bits[-1]] = value


def _safe_collection(collection: str) -> str:
    if collection not in ALLOWED_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Unknown collection")
    return collection


def _public_uid(user: dict[str, Any]) -> str:
    return str(user["id"])


def _can_read_collection(user: dict[str, Any], collection: str) -> bool:
    role = user["role"]
    allowed = ADMIN_READABLE if role == "admin" else CHEF_READABLE if role == "chef" else MEMBER_READABLE
    return collection in allowed


def _authorize_read(user: dict[str, Any], collection: str, doc_id: str | None = None, data: dict[str, Any] | None = None) -> None:
    collection = _safe_collection(collection)
    if collection == "users":
        if user["role"] != "admin" and doc_id != _public_uid(user):
            raise HTTPException(status_code=403, detail="Not allowed")
        return
    if not _can_read_collection(user, collection):
        raise HTTPException(status_code=403, detail="Not allowed")
    if collection == "payments" and user["role"] == "member" and data is not None:
        if str(data.get("uid", "")) != _public_uid(user):
            raise HTTPException(status_code=403, detail="Not allowed")


def _authorize_write(user: dict[str, Any], collection: str, op: str, doc_id: str, data: dict[str, Any] | None = None) -> None:
    collection = _safe_collection(collection)
    role = user["role"]
    uid = _public_uid(user)
    data = data or {}

    if collection in {"members", "payments", "monthlyClosings", "settings", "notifications", "system", "users"}:
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        return
    if collection == "inventory":
        if op == "delete" and role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        if role not in {"admin", "chef"}:
            raise HTTPException(status_code=403, detail="Admin or Chef required")
        return
    if collection == "meals":
        if op == "delete" and role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        if role not in {"admin", "chef"}:
            raise HTTPException(status_code=403, detail="Admin or Chef required")
        return
    if collection == "expenses":
        if op in {"update", "delete"} and role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        if op in {"create", "set"} and role not in {"admin", "chef"}:
            raise HTTPException(status_code=403, detail="Admin or Chef required")
        return
    if collection == "pushTokens":
        if doc_id != uid and role != "admin":
            raise HTTPException(status_code=403, detail="Not allowed")
        return
    if collection == "mealSkips":
        if role == "admin":
            return
        if role != "member":
            raise HTTPException(status_code=403, detail="Member required")
        if str(data.get("uid", "")) != uid:
            raise HTTPException(status_code=403, detail="Cannot change another member's skip")
        cutoff = data.get("cutoffAt")
        if cutoff:
            try:
                dt = datetime.fromisoformat(str(cutoff).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt <= datetime.now(timezone.utc):
                    raise HTTPException(status_code=409, detail="Meal skip cutoff has passed")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid meal skip cutoff")
        return
    raise HTTPException(status_code=403, detail="Not allowed")


def create_compat_router(db, current_user, allow_roles, hash_password):
    router = APIRouter(prefix="/compat", tags=["TECH MANZ compatibility"])
    bill_root = Path(os.getenv("STORAGE_ROOT", "/data")) / "bills"
    bill_root.mkdir(parents=True, exist_ok=True)

    def _fetch_doc(cur, collection: str, doc_id: str) -> dict[str, Any] | None:
        cur.execute("SELECT data FROM live_documents WHERE collection=%s AND doc_id=%s", (collection, doc_id))
        row = cur.fetchone()
        return row[0] if row else None

    def _sync_user_row(cur, doc_id: str, data: dict[str, Any]) -> None:
        try:
            user_id = uuid.UUID(doc_id)
        except Exception:
            return
        active = bool(data.get("active", True)) and not bool(data.get("removed", False))
        role = data.get("role") if data.get("role") in {"admin", "chef", "member"} else None
        cur.execute(
            """
            UPDATE users SET
              name=COALESCE(%s,name),
              phone=COALESCE(%s,phone),
              role=COALESCE(%s,role),
              active=%s,
              updated_at=NOW()
            WHERE id=%s
            """,
            (data.get("name") or None, data.get("phone") or None, role, active, user_id),
        )

    def _put_doc(cur, collection: str, doc_id: str, payload: dict[str, Any], merge: bool, user: dict[str, Any]) -> dict[str, Any]:
        collection = _safe_collection(collection)
        payload = _resolve_server_timestamps(payload or {})
        current = _fetch_doc(cur, collection, doc_id)
        op = "update" if current is not None else "create"
        _authorize_write(user, collection, op if merge else "set", doc_id, payload)
        final = _deep_merge(current or {}, payload) if merge else payload
        final.setdefault("updatedAt", _now_iso())
        if current is None:
            final.setdefault("createdAt", _now_iso())
        cur.execute(
            """
            INSERT INTO live_documents(collection,doc_id,data,created_at,updated_at)
            VALUES(%s,%s,%s,NOW(),NOW())
            ON CONFLICT(collection,doc_id)
            DO UPDATE SET data=EXCLUDED.data,updated_at=NOW()
            """,
            (collection, doc_id, psycopg.types.json.Jsonb(final)),
         )
        if collection == "users":
            _sync_user_row(cur, doc_id, final)
        return final

    @router.get("/public/system/config")
    def public_system_config():
        with db() as conn:
            with conn.cursor() as cur:
                data = _fetch_doc(cur, "system", "config")
        return {"id": "config", "exists": bool(data), "data": data or {}}

    @router.post("/auth/create")
    def create_auth_user(req: CompatCreateUser, admin=Depends(allow_roles("admin"))):
        user_id = uuid.uuid4()
        email = str(req.email).lower()
        name = (req.name or email.split("@", 1)[0]).strip()[:120]
        try:
            with db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users(id,name,email,role,active,password_hash)
                        VALUES(%s,%s,%s,'member',TRUE,%s)
                        """,
                        (user_id, name, email, hash_password(req.password)),
                    )
                    seed = {
                        "uid": str(user_id), "name": name, "email": email,
                        "role": "member", "active": True, "createdAt": _now_iso(),
                    }
                    cur.execute(
                        "INSERT INTO live_documents(collection,doc_id,data) VALUES('users',%s,%s)",
                        (str(user_id), psycopg.types.json.Jsonb(seed)),
                    )
                conn.commit()
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=409, detail="Email already exists")
        return {"uid": str(user_id), "email": email}

    @router.post("/auth/reset-password")
    def reset_auth_password(req: CompatResetPassword, admin=Depends(allow_roles("admin"))):
        email = str(req.email).lower()
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash=%s,updated_at=NOW() WHERE lower(email)=lower(%s) RETURNING id",
                    (hash_password(req.password), email),
                )
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404, detail="User not found")
            conn.commit()
        return {"status": "updated"}

    @router.get("/docs/{collection}")
    def list_docs(collection: str, field: str | None = None, eq: str | None = None, user=Depends(current_user)):
        collection = _safe_collection(collection)
        _authorize_read(user, collection)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT doc_id,data FROM live_documents WHERE collection=%s ORDER BY updated_at,doc_id",
                    (collection,),
                )
                rows = cur.fetchall()
        docs = []
        for doc_id, data in rows:
            if field is not None and str((data or {}).get(field, "")) != str(eq or ""):
                continue
            try:
                _authorize_read(user, collection, str(doc_id), data or {})
            except HTTPException:
                continue
            docs.append({"id": str(doc_id), "data": data or {}})
        return {"docs": docs}

    @router.post("/docs/{collection}")
    def add_doc(collection: str, payload: dict[str, Any], user=Depends(current_user)):
        doc_id = str(uuid.uuid4())
        with db() as conn:
            with conn.cursor() as cur:
                final = _put_doc(cur, collection, doc_id, payload, False, user)
            conn.commit()
        return {"id": doc_id, "data": final}

    @router.get("/docs/{collection}/{doc_id}")
    def get_doc(collection: str, doc_id: str, user=Depends(current_user)):
        collection = _safe_collection(collection)
        with db() as conn:
            with conn.cursor() as cur:
                data = _fetch_doc(cur, collection, doc_id)
        if data is None:
            return {"id": doc_id, "exists": False, "data": {}}
        _authorize_read(user, collection, doc_id, data)
        return {"id": doc_id, "exists": True, "data": data}

    @router.put("/docs/{collection}/{doc_id}")
    def set_doc(collection: str, doc_id: str, payload: dict[str, Any], merge: bool = False, user=Depends(current_user)):
        with db() as conn:
            with conn.cursor() as cur:
                final = _put_doc(cur, collection, doc_id, payload, merge, user)
            conn.commit()
        return {"id": doc_id, "data": final}

    @router.patch("/docs/{collection}/{doc_id}")
    def update_doc(collection: str, doc_id: str, payload: dict[str, Any], user=Depends(current_user)):
        with db() as conn:
            with conn.cursor() as cur:
                if _fetch_doc(cur, collection, doc_id) is None:
                    raise HTTPException(status_code=404, detail="Document not found")
                final = _put_doc(cur, collection, doc_id, payload, True, user)
            conn.commit()
        return {"id": doc_id, "data": final}

    @router.delete("/docs/{collection}/{doc_id}")
    def delete_doc(collection: str, doc_id: str, user=Depends(current_user)):
        collection = _safe_collection(collection)
        with db() as conn:
            with conn.cursor() as cur:
                old = _fetch_doc(cur, collection, doc_id)
                if old is None:
                    return {"status": "missing"}
                _authorize_write(user, collection, "delete", doc_id, old)
                cur.execute("DELETE FROM live_documents WHERE collection=%s AND doc_id=%s", (collection, doc_id))
                if collection == "users":
                    try:
                        cur.execute("UPDATE users SET active=FALSE,updated_at=NOW() WHERE id=%s", (uuid.UUID(doc_id),))
                    except Exception:
                        pass
            conn.commit()
        return {"status": "deleted"}

    @router.post("/batch")
    def batch(req: BatchRequest, user=Depends(current_user)):
        results = []
        with db() as conn:
            with conn.cursor() as cur:
                for item in req.operations:
                    op = str(item.get("op", "")).lower()
                    collection = _safe_collection(str(item.get("collection", "")))
                    doc_id = str(item.get("id", ""))
                    if not doc_id:
                        raise HTTPException(status_code=422, detail="Batch document id required")
                    if op in {"set", "update"}:
                        current = _fetch_doc(cur, collection, doc_id)
                        if op == "update" and current is None:
                            raise HTTPException(status_code=404, detail=f"Missing {collection}/{doc_id}")
                        final = _put_doc(cur, collection, doc_id, item.get("data") or {}, bool(item.get("merge", op == "update")), user)
                        results.append({"id": doc_id, "data": final})
                    elif op == "delete":
                        old = _fetch_doc(cur, collection, doc_id)
                        if old is not None:
                            _authorize_write(user, collection, "delete", doc_id, old)
                            cur.execute("DELETE FROM live_documents WHERE collection=%s AND doc_id=%s", (collection, doc_id))
                            if collection == "users":
                                try:
                                    cur.execute("UPDATE users SET active=FALSE,updated_at=NOW() WHERE id=%s", (uuid.UUID(doc_id),))
                                    cur.execute("UPDATE members SET user_id=NULL,updated_at=NOW() WHERE user_id=%s", (uuid.UUID(doc_id),))
                                except Exception:
                                    pass
                        results.append({"id": doc_id, "deleted": True})
                    else:
                        raise HTTPException(status_code=422, detail=f"Unsupported batch op: {op}")
            conn.commit()
        return {"status": "ok", "results": results}

    @router.post("/files/bills")
    async def upload_bill(bill: UploadFile = File(...), user=Depends(allow_roles("admin", "chef"))):
        content_type = (bill.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="Bill must be an image")
        raw = await bill.read()
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Bill image exceeds 8 MB")
        ext = mimetypes.guess_extension(content_type.split(";", 1)[0]) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        name = f"{uuid.uuid4().hex}{ext}"
        (bill_root / name).write_bytes(raw)
        return {"billUrl": f"/api/compat/files/bills/{name}", "billFileId": name, "imageProvider": "local"}

    @router.get("/files/bills/{filename}")
    def get_bill_file(filename: str):
        safe = Path(filename).name
        path = bill_root / safe
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Bill not found")
        return FileResponse(path)

    return router
