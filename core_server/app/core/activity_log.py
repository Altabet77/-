import json
import logging
from typing import Optional, Dict, Any, List
import aiosqlite
from app.core.config import settings

logger = logging.getLogger("samir.activity_log")


class ActivityLogger:
    """سجل العمليات — يتتبع كل ما يفعله سمير"""

    def __init__(self):
        self.db_path = settings.DB_PATH

    async def log(
        self,
        event_type: str,
        summary: str,
        details: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: str = "success",
        session_id: Optional[str] = None,
    ) -> None:
        """تسجيل حدث في سجل العمليات"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO activity_logs
                        (event_type, summary, details, tool_name, status, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (event_type, summary, details, tool_name, status, session_id),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to write activity log: {e}")

    async def log_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> None:
        """تسجيل تنفيذ أداة"""
        status = result.get("status", "success")
        summary = f"تم تنفيذ: {tool_name}"
        if status == "error":
            summary = f"فشل تنفيذ: {tool_name}"
        elif status == "needs_confirmation":
            summary = f"طلب تأكيد: {tool_name}"

        await self.log(
            event_type="tool_executed",
            summary=summary,
            details=json.dumps(
                {"arguments": arguments, "result": result}, ensure_ascii=False
            ),
            tool_name=tool_name,
            status=status,
            session_id=session_id,
        )

    async def log_mode_activation(
        self, mode_name: str, session_id: Optional[str] = None
    ) -> None:
        """تسجيل تفعيل وضع"""
        await self.log(
            event_type="mode_activated",
            summary=f"تم تفعيل وضع: {mode_name}",
            tool_name="activate_mode",
            session_id=session_id,
        )

    async def log_memory_save(
        self, key: str, value: str, session_id: Optional[str] = None
    ) -> None:
        """تسجيل حفظ معلومة في الذاكرة"""
        await self.log(
            event_type="memory_saved",
            summary=f"تم حفظ: {key}",
            details=f"{key}: {value}",
            tool_name="save_memory",
            session_id=session_id,
        )

    async def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """جلب آخر العمليات المسجلة"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def clear_logs(self) -> int:
        """حذف جميع السجلات"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM activity_logs")
            await db.commit()
            return cursor.rowcount


activity_logger = ActivityLogger()
