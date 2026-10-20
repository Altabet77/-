import aiosqlite
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger("samir.api.devices")
router = APIRouter(prefix="/devices", tags=["Device Management"])

class DeviceRegisterRequest(BaseModel):
    id: str
    name: str
    device_type: str  # 'windows', 'android', 'web'
    token: str

@router.get("", response_model=List[dict])
async def list_devices():
    """عرض قائمة الأجهزة المسجلة وحالة اتصالها"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name, device_type, status, ip_address, last_seen FROM devices ORDER BY last_seen DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("/register")
async def register_device(req: DeviceRegisterRequest):
    """تسجيل أو تحديث جهاز جديد في شبكة سمير"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("""
            INSERT INTO devices (id, name, device_type, token, status, last_seen)
            VALUES (?, ?, ?, ?, 'online', CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                device_type = excluded.device_type,
                token = excluded.token,
                status = 'online',
                last_seen = CURRENT_TIMESTAMP;
        """, (req.id, req.name, req.device_type, req.token))
        await db.commit()
    return {"status": "success", "message": f"Device '{req.name}' registered successfully."}
