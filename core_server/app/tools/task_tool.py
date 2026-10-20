import json
import logging
from typing import Dict, Any, Optional, List
import aiosqlite
from app.tools.base_tool import tool_registry
from app.core.config import settings

logger = logging.getLogger("samir.tools.tasks")


async def tool_create_task(
    title: str,
    description: Optional[str] = None,
    priority: str = "normal",
    category: str = "general",
    due_date: Optional[str] = None,
    reminder_at: Optional[str] = None,
) -> Dict[str, Any]:
    """إنشاء مهمة أو تذكير جديد"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO tasks (title, description, priority, category, due_date, reminder_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, description, priority, category, due_date, reminder_at),
        )
        await db.commit()
        task_id = cursor.lastrowid
        row = await (await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))).fetchone()
        return {"created": True, "task": dict(row) if row else {"id": task_id, "title": title}}


async def tool_list_tasks(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """جلب قائمة المهام"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params: List[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        else:
            # افتراضيًا، أظهر فقط المهام غير المكتملة
            conditions.append("status NOT IN ('done', 'cancelled')")

        if category:
            conditions.append("category = ?")
            params.append(category)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)

        cursor = await db.execute(
            f"SELECT * FROM tasks {where_clause} ORDER BY priority DESC, created_at DESC LIMIT ?",
            params,
        )
        rows = await cursor.fetchall()
        tasks = [dict(r) for r in rows]

        if not tasks:
            return {"found": False, "tasks": [], "message": "ما عندك مهام في هذه الفئة."}

        return {"found": True, "count": len(tasks), "tasks": tasks}


async def tool_complete_task(task_id: int) -> Dict[str, Any]:
    """تحديث حالة مهمة إلى مكتملة"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE tasks SET status='done', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (task_id,),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return {"updated": False, "message": f"ما لقيت مهمة بالرقم {task_id}."}
        return {"updated": True, "message": f"تم تحديد المهمة رقم {task_id} كمكتملة."}


async def tool_delete_task(task_id: int) -> Dict[str, Any]:
    """حذف مهمة"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()
        if cursor.rowcount == 0:
            return {"deleted": False, "message": f"ما لقيت مهمة بالرقم {task_id}."}
        return {"deleted": True, "message": f"تم حذف المهمة رقم {task_id}."}


def register_task_tools():
    tool_registry.register_tool(
        name="create_task",
        description=(
            "إنشاء مهمة أو تذكير جديد. استخدم عندما يقول المستخدم 'ذكرني'، "
            "'لازم أسوي'، 'اكتب في قائمتي'، أو أي طلب لحفظ مهمة."
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "عنوان المهمة أو التذكير (مثال: 'تسجيل فيديو اليوتيوب')",
                },
                "description": {
                    "type": "string",
                    "description": "تفاصيل اختيارية للمهمة",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "أولوية المهمة",
                },
                "category": {
                    "type": "string",
                    "description": "تصنيف المهمة (مثال: 'youtube', 'work', 'personal', 'gaming')",
                },
                "due_date": {
                    "type": "string",
                    "description": "تاريخ الاستحقاق (مثال: '2026-09-11' أو 'غداً')",
                },
                "reminder_at": {
                    "type": "string",
                    "description": "وقت التذكير (مثال: '2026-09-11T09:00:00')",
                },
            },
            "required": ["title"],
        },
        handler=tool_create_task,
    )

    tool_registry.register_tool(
        name="list_tasks",
        description=(
            "جلب قائمة المهام الحالية. استخدم عندما يسأل المستخدم 'شن باقي عليّ'، "
            "'شنو مهامي'، 'عرضلي اللي لازم أسوي'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done", "cancelled"],
                    "description": "فلترة حسب الحالة (اختياري — بدون فلتر يُظهر المهام غير المكتملة)",
                },
                "category": {
                    "type": "string",
                    "description": "فلترة حسب التصنيف (اختياري)",
                },
                "limit": {
                    "type": "integer",
                    "description": "عدد المهام المطلوب إظهاره (افتراضي: 10)",
                },
            },
            "required": [],
        },
        handler=tool_list_tasks,
    )

    tool_registry.register_tool(
        name="complete_task",
        description="تحديد مهمة كمكتملة. استخدم عندما يقول المستخدم 'خلصت' أو 'انتهيت من' مهمة معينة.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "رقم المهمة المراد تحديثها",
                }
            },
            "required": ["task_id"],
        },
        handler=tool_complete_task,
    )

    tool_registry.register_tool(
        name="delete_task",
        description="حذف مهمة نهائيًا.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "رقم المهمة المراد حذفها",
                }
            },
            "required": ["task_id"],
        },
        handler=tool_delete_task,
    )


register_task_tools()
