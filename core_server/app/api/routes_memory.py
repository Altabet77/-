import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.memory.long_term import long_term_memory

logger = logging.getLogger("samir.api.memory")
router = APIRouter(prefix="/memory", tags=["Memory Management"])

class MemoryItemCreate(BaseModel):
    key: str
    value: str
    category: Optional[str] = "general"

class MemoryItemResponse(BaseModel):
    id: int
    key: str
    value: str
    category: str
    is_user_approved: bool
    created_at: str
    updated_at: str

@router.get("", response_model=List[dict])
async def list_memories():
    """عرض جميع الحقائق المحفوظة في الذاكرة الدائمة"""
    return await long_term_memory.get_all_facts()

@router.post("", response_model=dict)
async def create_memory(item: MemoryItemCreate):
    """إضافة أو تحديث معلومة في الذاكرة الدائمة"""
    return await long_term_memory.save_fact(
        key=item.key,
        value=item.value,
        category=item.category or "general"
    )

@router.delete("/{memory_id}")
async def delete_memory(memory_id: int):
    """حذف معلومة من الذاكرة"""
    deleted = await long_term_memory.delete_fact(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"status": "success", "message": f"Memory item {memory_id} deleted."}


# ─── أوامر وقواعد وبرومبتات المستخدم المخصصة الدائمة (Custom Commands & Prompts) ───
class CustomPromptCreate(BaseModel):
    topic: str
    instruction: str

@router.get("/custom-rules")
async def list_custom_rules():
    """عرض جميع الأوامر والتعليمات والبرومبتات الخاصة التي أضافها المستخدم لسمير"""
    import aiosqlite
    from app.core.config import settings
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, topic, correction, context, created_at FROM learned_lessons ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("/custom-rules")
async def add_custom_rule(item: CustomPromptCreate):
    """إضافة أمر أو برومبت يدوي جديد لسمير لحفظه في عقله الدائم"""
    import aiosqlite
    from app.core.config import settings
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO learned_lessons (topic, correction, context) VALUES (?, ?, ?)",
            (item.topic.strip() or "أمر مخصص", item.instruction.strip(), "manual_rule")
        )
        await db.commit()
        rule_id = cursor.lastrowid
    return {
        "status": "success",
        "id": rule_id,
        "topic": item.topic,
        "instruction": item.instruction,
        "message": "تم حفظ الأمر في ذاكرة وقواعد سمير بنجاح! ✓"
    }

@router.delete("/custom-rules/{rule_id}")
async def delete_custom_rule(rule_id: int):
    """حذف أمر أو برومبت يدوي"""
    import aiosqlite
    from app.core.config import settings
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute("DELETE FROM learned_lessons WHERE id = ?", (rule_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "success", "message": f"تم حذف الأمر {rule_id} بنجاح."}
