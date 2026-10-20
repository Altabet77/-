import aiosqlite
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.memory.short_term import short_term_memory
from app.memory.long_term import long_term_memory
from app.core.config import settings

logger = logging.getLogger("samir.memory.manager")

class MemoryManager:
    """المنسق المركزي للذاكرة المزدوجة والمحادثات الدائمة في سمير"""

    def __init__(self):
        self.short_term = short_term_memory
        self.long_term = long_term_memory

    async def get_full_context(self, session_id: str, current_query: str) -> Dict[str, Any]:
        """
        جلب سياق المحادثة (من الذاكرة السريعة، أو استرجاعه من قاعدة البيانات إن كان فارغاً)
        بالإضافة للحقائق طويلة الأمد المخزنة
        """
        history = self.short_term.get_history(session_id)
        if not history:
            # محاولة استرجاع آخر رسائل من قاعدة البيانات لنفس الجلسة
            db_history = await self.get_recent_session_history(session_id, limit=20)
            for msg in db_history:
                role = "user" if msg["sender"] == "user" else "assistant"
                self.short_term.add_message(session_id, role, msg["content"])
            history = self.short_term.get_history(session_id)

        facts = await self.long_term.get_all_facts()

        return {
            "history": history,
            "facts": facts
        }

    async def record_interaction(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        routing_reason: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """تسجيل التبادل الحواري في الذاكرة السريعة + حفظه الدائم في SQLite مع ربطه بالجهاز أو المستخدم"""
        # 1. الذاكرة قصيرة المدى (RAM)
        self.short_term.add_message(session_id, "user", user_text)
        self.short_term.add_message(session_id, "assistant", assistant_text)

        # 2. الحفظ الدائم في SQLite
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row

                # التأكد من وجود سجل المحادثة
                cursor = await db.execute("SELECT id, title, message_count FROM conversations WHERE id = ?", (session_id,))
                conv = await cursor.fetchone()

                now = datetime.utcnow().isoformat()
                if not conv:
                    # توليد عنوان ذكي ومختصر من أول رسالة
                    clean_title = user_text.strip().replace("\n", " ")
                    title = clean_title[:45] + ("..." if len(clean_title) > 45 else "")
                    if not title:
                        title = "محادثة جديدة"

                    await db.execute(
                        """
                        INSERT INTO conversations (id, title, summary, provider_used, message_count, created_at, updated_at, device_id, user_id)
                        VALUES (?, ?, ?, ?, 2, ?, ?, ?, ?)
                        """,
                        (session_id, title, "", provider or "auto", now, now, device_id or "", str(user_id) if user_id else "")
                    )
                else:
                    await db.execute(
                        """
                        UPDATE conversations 
                        SET message_count = message_count + 2, 
                            updated_at = ?,
                            provider_used = COALESCE(?, provider_used),
                            device_id = CASE WHEN device_id IS NULL OR device_id = '' THEN ? ELSE device_id END,
                            user_id = CASE WHEN ? != '' THEN ? ELSE user_id END
                        WHERE id = ?
                        """,
                        (now, provider, device_id or "", str(user_id) if user_id else "", str(user_id) if user_id else "", session_id)
                    )

                # حفظ رسالة المستخدم
                await db.execute(
                    """
                    INSERT INTO messages (conversation_id, session_id, sender, content, provider, model, created_at)
                    VALUES (?, ?, 'user', ?, ?, ?, ?)
                    """,
                    (session_id, session_id, user_text, provider, model, now)
                )

                # حفظ رد المساعد
                import json
                tc_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
                await db.execute(
                    """
                    INSERT INTO messages (conversation_id, session_id, sender, content, provider, model, routing_reason, tool_calls_json, created_at)
                    VALUES (?, ?, 'samir', ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, session_id, assistant_text, provider, model, routing_reason, tc_json, now)
                )

                await db.commit()
                logger.info(f"Interaction persisted permanently for session: {session_id}")
        except Exception as e:
            logger.error(f"Error persisting interaction to SQLite: {e}", exc_info=True)

    async def get_recent_session_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """جلب الرسائل السابقة لجلسة معينة من قاعدة البيانات"""
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT sender, content, provider, model, created_at 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY id ASC 
                    LIMIT ?
                    """,
                    (session_id, limit)
                )
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to fetch session history from DB: {e}")
            return []

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """جلب قائمة بالمحادثات المعزولة والخاصة بهذا الجهاز أو هذا المستخدم فقط"""
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row

                if user_id:
                    # المستخدم مسجل دخول — عرض محادثات حسابه فقط
                    cursor = await db.execute(
                        """
                        SELECT id, title, summary, provider_used, message_count, created_at, updated_at
                        FROM conversations
                        WHERE user_id = ?
                        ORDER BY updated_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (str(user_id), limit, offset)
                    )
                elif device_id:
                    # زائر أو مستخدم محلي — عرض محادثات جهازه فقط (بدون تسريب محادثات الآخرين)
                    cursor = await db.execute(
                        """
                        SELECT id, title, summary, provider_used, message_count, created_at, updated_at
                        FROM conversations
                        WHERE device_id = ? AND (user_id IS NULL OR user_id = '')
                        ORDER BY updated_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (str(device_id), limit, offset)
                    )
                else:
                    # عند عدم تمرير أي معرف جهاز، لا نكشف محادثات الآخرين
                    return []

                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """جلب كل رسائل محادثة معينة بالتفصيل"""
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT id, sender, content, provider, model, routing_reason, tool_calls_json, created_at
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id ASC
                    """,
                    (conversation_id,)
                )
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []

    async def delete_conversation(self, conversation_id: str) -> bool:
        """حذف محادثة بالكامل ورسائلها"""
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                await db.commit()
            self.short_term.clear_session(conversation_id)
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False

    async def resume_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """استئناف محادثة قديمة وتحميل رسائلها في الذاكرة السريعة للجلسة الحالية"""
        messages = await self.get_conversation_messages(conversation_id)
        self.short_term.clear_session(conversation_id)
        for msg in messages:
            role = "user" if msg["sender"] == "user" else "assistant"
            self.short_term.add_message(conversation_id, role, msg["content"])
        
        return {
            "conversation_id": conversation_id,
            "messages_loaded": len(messages),
            "status": "resumed"
        }

    async def store_user_fact(self, key: str, value: str, category: str = "general") -> Dict[str, Any]:
        """حفظ حقيقة دائمة"""
        return await self.long_term.save_fact(key, value, category)

memory_manager = MemoryManager()
