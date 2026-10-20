import logging
import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger("samir.api.custom_rules")

# ─── راوتر مستقل تماماً لأوامر وبرومبتات المستخدم ───
# المسار: /api/v1/custom-rules  (بعيداً عن /memory لتجنب تعارض /{memory_id})
router = APIRouter(prefix="/custom-rules", tags=["Custom Rules & Prompts"])


class CustomPromptCreate(BaseModel):
    topic: str
    instruction: str


@router.get("")
async def list_custom_rules():
    """عرض جميع الأوامر والبرومبتات الخاصة التي حفظها المستخدم في عقل سمير"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, topic, correction, context, created_at FROM learned_lessons "
            "WHERE context = 'manual_rule' ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.post("")
async def add_custom_rule(item: CustomPromptCreate):
    """إضافة أمر أو برومبت جديد لسمير لحفظه في عقله الدائم"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO learned_lessons (topic, correction, context) VALUES (?, ?, ?)",
            (item.topic.strip() or "أمر مخصص", item.instruction.strip(), "manual_rule")
        )
        await db.commit()
        rule_id = cursor.lastrowid
    logger.info(f"Custom rule saved: [{item.topic}] id={rule_id}")
    return {
        "status": "success",
        "id": rule_id,
        "topic": item.topic,
        "instruction": item.instruction,
        "message": "تم حفظ الأمر في ذاكرة وقواعد سمير بنجاح! ✓"
    }


@router.delete("/{rule_id}")
async def delete_custom_rule(rule_id: int):
    """حذف أمر أو برومبت من ذاكرة سمير"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM learned_lessons WHERE id = ? AND context = 'manual_rule'",
            (rule_id,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
    logger.info(f"Custom rule deleted: id={rule_id}")
    return {"status": "success", "message": f"تم حذف الأمر {rule_id} بنجاح."}
