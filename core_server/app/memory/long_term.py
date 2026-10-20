import aiosqlite
import logging
from contextvars import ContextVar
from typing import List, Dict, Optional, Any
from app.core.config import settings

logger = logging.getLogger("samir.memory.long_term")

# سياق المستخدم الحالي النشط للجلسة
current_user_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar("current_user", default=None)

class LongTermMemory:
    """إدارة الذاكرة طويلة المدى المخصصة والمعزولة لكل مستخدم مسجل عبر Google"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DB_PATH

    async def save_fact(
        self,
        key: str,
        value: str,
        category: str = "general",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """حفظ أو تحديث حقيقة صريحة في الذاكرة الخاصة بالمستخدم"""
        # محاولة جلب المستخدم من سياق الجلسة إذا لم يُمرر صراحة
        if user_id is None:
            active_u = current_user_var.get()
            if active_u and active_u.get("id"):
                user_id = active_u.get("id")

        if not user_id:
            # لم يسجل المستخدم دخوله بعد — لا يتم تسجيل الذكريات بدون تسجيل دخول Google
            logger.info("Attempted to save memory without Google login. Denied.")
            return {
                "saved": False,
                "reason": "login_required",
                "message": "لم يتم حفظ الذاكرة لأنك لست مسجلاً بحساب Google. قم بتسجيل الدخول لبدء حفظ ذكرياتك الخاصة."
            }

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("""
                INSERT INTO user_memories (user_id, key, value, category, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, key, value, category))
            await db.commit()

            cursor = await db.execute(
                "SELECT * FROM user_memories WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            row = await cursor.fetchone()
            logger.info(f"Saved memory for user {user_id}: {key} = {value}")
            return dict(row) if row else {"key": key, "value": value, "user_id": user_id}

    async def get_all_facts(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """جلب جميع الحقائق المحفوظة في الذاكرة للمستخدم الحالي فقط"""
        if user_id is None:
            active_u = current_user_var.get()
            if active_u and active_u.get("id"):
                user_id = active_u.get("id")

        if not user_id:
            # بدون تسجيل الدخول تكون الذاكرة نظيفة تماماً ولا تحتوي على أي بيانات سابقة
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, key, value, category, updated_at FROM user_memories WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def delete_fact(self, memory_id: int, user_id: Optional[int] = None) -> bool:
        """حذف معلومة من ذاكرة المستخدم"""
        if user_id is None:
            active_u = current_user_var.get()
            if active_u and active_u.get("id"):
                user_id = active_u.get("id")

        async with aiosqlite.connect(self.db_path) as db:
            if user_id:
                cursor = await db.execute(
                    "DELETE FROM user_memories WHERE id = ? AND user_id = ?",
                    (memory_id, user_id)
                )
            else:
                cursor = await db.execute("DELETE FROM user_memories WHERE id = ?", (memory_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def clear_all_user_memories(self, user_id: int) -> bool:
        """مسح كامل ذكريات المستخدم لبدء صفحة جديدة"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
            await db.commit()
        return True

    async def search_facts(self, query: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """بحث في ذاكرة المستخدم بالكلمات المفتاحية"""
        if user_id is None:
            active_u = current_user_var.get()
            if active_u and active_u.get("id"):
                user_id = active_u.get("id")

        if not user_id:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            search_pattern = f"%{query}%"
            cursor = await db.execute("""
                SELECT * FROM user_memories 
                WHERE user_id = ? AND (key LIKE ? OR value LIKE ?) 
                ORDER BY updated_at DESC
            """, (user_id, search_pattern, search_pattern))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

long_term_memory = LongTermMemory()
