import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import aiosqlite
from app.core.config import settings

logger = logging.getLogger("samir.api.tasks")
router = APIRouter(prefix="/tasks", tags=["Task Manager"])


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "normal"
    category: str = "general"
    due_date: Optional[str] = None
    reminder_at: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    reminder_at: Optional[str] = None


@router.get("/")
async def list_tasks(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """جلب قائمة المهام"""
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status)
            else:
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

        return {"count": len(tasks), "tasks": tasks}
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_task(req: CreateTaskRequest):
    """إنشاء مهمة جديدة"""
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                INSERT INTO tasks (title, description, priority, category, due_date, reminder_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (req.title, req.description, req.priority, req.category, req.due_date, req.reminder_at),
            )
            await db.commit()
            task_id = cursor.lastrowid
            row = await (await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))).fetchone()
            return {"created": True, "task": dict(row) if row else {"id": task_id}}
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{task_id}")
async def update_task(task_id: int, req: UpdateTaskRequest):
    """تحديث مهمة موجودة"""
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="لا توجد حقول للتحديث.")

        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        set_clause += ", updated_at=CURRENT_TIMESTAMP"
        values = list(updates.values()) + [task_id]

        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"UPDATE tasks SET {set_clause} WHERE id=?", values
            )
            await db.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"ما لقيت مهمة بالرقم {task_id}.")
            row = await (await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))).fetchone()
            return {"updated": True, "task": dict(row) if row else {}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """حذف مهمة"""
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            await db.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"ما لقيت مهمة بالرقم {task_id}.")
        return {"deleted": True, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modes/")
async def get_modes():
    """جلب أوضاع سمير المتاحة"""
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM modes ORDER BY id")
            rows = await cursor.fetchall()
            return {"modes": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modes/{mode_name}/activate")
async def activate_mode(mode_name: str):
    """تفعيل وضع معين من الأوضاع المتاحة"""
    try:
        from app.tools.modes_tool import tool_activate_mode
        res = await tool_activate_mode(mode_name)
        return res
    except Exception as e:
        logger.error(f"Error activating mode {mode_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
