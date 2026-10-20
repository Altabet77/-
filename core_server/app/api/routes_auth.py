"""
مسارات المصادقة وحسابات المستخدمين لسمير (Samir Accounts & Isolated Memory)
يدعم تسجيل الدخول المباشر وإنشاء الحساب ببريد Google أو أي بريد وكلمة مرور
كل مستخدم يحصل على ذاكرة خاصة معزولة تماماً محمية بحسابه
"""
import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("samir.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SALT = "_samir_auth_secure_salt_2026_"


def hash_password(password: str) -> str:
    """تشفير كلمة المرور بـ SHA-256 + Salt"""
    if not password:
        return ""
    salted = f"{password}{SALT}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """التحقق من صحة كلمة المرور"""
    if not hashed_password:
        return True  # حساب قديم بدون كلمة مرور
    if not plain_password:
        return False
    return hash_password(plain_password) == hashed_password


def generate_avatar_url(seed: str) -> str:
    """توليد صورة رمزية جميلة مستندة للبريد أو الاسم"""
    encoded = base64.b64encode(seed.encode("utf-8")).decode("ascii")[:12]
    return f"https://api.dicebear.com/7.x/bottts/svg?seed={encoded}"


# ── Pydantic Models ──────────────────────────────────────────────────────────

class GoogleTokenPayload(BaseModel):
    google_id: str
    email: str
    name: str
    picture: Optional[str] = None


class RegisterPayload(BaseModel):
    email: str
    name: str
    password: Optional[str] = ""
    picture: Optional[str] = None


class LoginPayload(BaseModel):
    email: str
    password: Optional[str] = ""


class QuickLoginPayload(BaseModel):
    email: str
    name: Optional[str] = None


class AuthResponse(BaseModel):
    session_token: str
    user_id: int
    name: str
    email: str
    picture: Optional[str] = None
    created_new: bool = False


# ── Auth Endpoints ───────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register_user(payload: RegisterPayload):
    """
    إنشاء حساب جديد للمستخدم مع حفظ كلمة المرور المشفرة
    """
    clean_email = payload.email.strip().lower()
    clean_name = payload.name.strip()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="يرجى إدخال بريد إلكتروني صحيح")
    if not clean_name:
        clean_name = clean_email.split("@")[0]

    pwd_hash = hash_password(payload.password) if payload.password else ""
    session_token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()
    google_id = "acc_" + hashlib.md5(clean_email.encode()).hexdigest()[:16]
    picture = payload.picture or generate_avatar_url(clean_email)

    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # التحقق إن كان البريد مسجلاً مسبقاً
        cursor = await db.execute("SELECT * FROM users WHERE LOWER(email) = ?", (clean_email,))
        existing = await cursor.fetchone()

        if existing:
            # إذا كان موجوداً بالفعل:
            if existing["password_hash"]:
                if payload.password and verify_password(payload.password, existing["password_hash"]):
                    # كلمة المرور صحيحة، نسجله مباشرة
                    await db.execute(
                        "UPDATE users SET session_token = ?, last_login = ? WHERE id = ?",
                        (session_token, now, existing["id"])
                    )
                    await db.commit()
                    return AuthResponse(
                        session_token=session_token,
                        user_id=existing["id"],
                        name=existing["name"],
                        email=existing["email"],
                        picture=existing["picture"] or picture,
                        created_new=False,
                    )
                raise HTTPException(status_code=400, detail="هذا البريد مسجل مسبقاً بالفعل! يرجى اختيار 'تسجيل الدخول' أو إدخال كلمة المرور الصحيحة.")
            else:
                # حساب قديم بدون كلمة مرور: نحدث كلمة المرور ونسجله
                await db.execute(
                    "UPDATE users SET name = ?, password_hash = ?, session_token = ?, last_login = ? WHERE id = ?",
                    (clean_name, pwd_hash, session_token, now, existing["id"])
                )
                await db.commit()
                return AuthResponse(
                    session_token=session_token,
                    user_id=existing["id"],
                    name=clean_name,
                    email=existing["email"],
                    picture=existing["picture"] or picture,
                    created_new=False,
                )

        # إضافة مستخدم جديد
        cursor = await db.execute(
            """INSERT INTO users (google_id, email, name, picture, session_token, password_hash, created_at, last_login)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (google_id, clean_email, clean_name, picture, session_token, pwd_hash, now, now)
        )
        user_id = cursor.lastrowid
        await db.commit()

    logger.info(f"New user registered: {clean_email} (id={user_id})")
    return AuthResponse(
        session_token=session_token,
        user_id=user_id,
        name=clean_name,
        email=clean_email,
        picture=picture,
        created_new=True,
    )


@router.post("/login", response_model=AuthResponse)
async def login_user(payload: LoginPayload):
    """
    تسجيل الدخول بحساب موجود (بالبريد وكلمة المرور)
    """
    clean_email = payload.email.strip().lower()
    if not clean_email:
        raise HTTPException(status_code=400, detail="يرجى إدخال البريد الإلكتروني")

    session_token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM users WHERE LOWER(email) = ? OR google_id = ?",
            (clean_email, clean_email)
        )
        user = await cursor.fetchone()

        if not user:
            # إذا لم يكن مسجلاً، نسجل له حساباً سريعاً إذا لم تكن كلمة المرور مطلوبة أو نطلب التسجيل
            # لتسهيل تجربة المستخدم: إذا كان يدخل أول مرة، ننشئ له الحساب فوراً!
            clean_name = clean_email.split("@")[0]
            pwd_hash = hash_password(payload.password) if payload.password else ""
            google_id = "acc_" + hashlib.md5(clean_email.encode()).hexdigest()[:16]
            picture = generate_avatar_url(clean_email)

            cur_ins = await db.execute(
                """INSERT INTO users (google_id, email, name, picture, session_token, password_hash, created_at, last_login)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (google_id, clean_email, clean_name, picture, session_token, pwd_hash, now, now)
            )
            user_id = cur_ins.lastrowid
            await db.commit()
            logger.info(f"Auto-created user on first login: {clean_email} (id={user_id})")
            return AuthResponse(
                session_token=session_token,
                user_id=user_id,
                name=clean_name,
                email=clean_email,
                picture=picture,
                created_new=True,
            )

        # التحقق من كلمة المرور
        user_dict = dict(user)
        user_pwd_hash = user_dict.get("password_hash")

        if user_pwd_hash:
            if not verify_password(payload.password, user_pwd_hash):
                raise HTTPException(status_code=401, detail="كلمة المرور غير صحيحة، يرجى التأكد والمحاولة ثانية")
        elif payload.password:
            # الحساب قديم ولم تكن له كلمة مرور، نحفظها له الآن
            new_hash = hash_password(payload.password)
            await db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user["id"])
            )

        # تحديث الجلسة
        await db.execute(
            "UPDATE users SET session_token = ?, last_login = ? WHERE id = ?",
            (session_token, now, user["id"])
        )
        await db.commit()

    logger.info(f"User logged in: {user['email']} (id={user['id']})")
    return AuthResponse(
        session_token=session_token,
        user_id=user["id"],
        name=user["name"],
        email=user["email"],
        picture=user["picture"] or generate_avatar_url(user["email"]),
        created_new=False,
    )


@router.post("/quick", response_model=AuthResponse)
async def quick_login(payload: QuickLoginPayload):
    """
    تسجيل دخول سريع وفوري بالبريد الإلكتروني فقط
    """
    clean_email = payload.email.strip().lower()
    clean_name = (payload.name or "").strip() or clean_email.split("@")[0]
    return await login_user(LoginPayload(email=clean_email, password=""))


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleTokenPayload):
    """
    متوافق مع أي استدعاء قديم لـ Google OAuth
    """
    session_token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM users WHERE google_id = ? OR LOWER(email) = ?",
            (payload.google_id, payload.email.lower())
        )
        user = await cursor.fetchone()

        if user:
            await db.execute(
                """UPDATE users SET 
                   name = ?, picture = COALESCE(?, picture), session_token = ?, last_login = ?
                   WHERE id = ?""",
                (payload.name, payload.picture, session_token, now, user["id"])
            )
            user_id = user["id"]
        else:
            cursor = await db.execute(
                """INSERT INTO users (google_id, email, name, picture, session_token, created_at, last_login)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (payload.google_id, payload.email.lower(), payload.name,
                 payload.picture or generate_avatar_url(payload.email), session_token, now, now)
            )
            user_id = cursor.lastrowid
            logger.info(f"New user registered via Google payload: {payload.email} (id={user_id})")

        await db.commit()

    return AuthResponse(
        session_token=session_token,
        user_id=user_id,
        name=payload.name,
        email=payload.email,
        picture=payload.picture or generate_avatar_url(payload.email),
    )


@router.get("/me")
async def get_current_user(token: str):
    """التحقق من صحة session_token وإعادة بيانات المستخدم"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, google_id, email, name, picture, created_at, last_login FROM users WHERE session_token = ?",
            (token,)
        )
        user = await cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return dict(user)


@router.delete("/memory/{user_id}")
async def clear_user_memory(user_id: int, token: str):
    """مسح جميع ذكريات مستخدم معين (يتطلب token خاص به)"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id FROM users WHERE id = ? AND session_token = ?",
            (user_id, token)
        )
        user = await cursor.fetchone()
        if not user:
            raise HTTPException(status_code=403, detail="Forbidden")

        await db.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
        await db.commit()

    logger.info(f"Cleared all memories for user_id={user_id}")
    return {"status": "success", "message": "تم مسح جميع الذكريات الخاصة بك بنجاح"}


@router.get("/memories/{user_id}")
async def get_user_memories(user_id: int, token: str):
    """جلب ذكريات مستخدم معين"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id FROM users WHERE id = ? AND session_token = ?",
            (user_id, token)
        )
        user = await cursor.fetchone()
        if not user:
            raise HTTPException(status_code=403, detail="Forbidden")

        cursor = await db.execute(
            "SELECT id, key, value, category, updated_at FROM user_memories WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        memories = await cursor.fetchall()

    return {"memories": [dict(m) for m in memories]}
