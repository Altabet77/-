import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger("samir.memory.short_term")

class ShortTermMemory:
    """إدارة سياق الجلسات الحالية والمحادثات قصيرة المدى"""

    def __init__(self, max_history_per_session: int = 20):
        self.max_history = max_history_per_session
        self.sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    def add_message(self, session_id: str, role: str, content: str):
        """إضافة رسالة إلى سياق المحادثة الحالي"""
        self.sessions[session_id].append({
            "role": role,
            "content": content
        })
        # الاحتفاظ بآخر N رسائل فقط
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """جلب تاريخ المحادثة للجلسة"""
        return self.sessions[session_id]

    def clear_session(self, session_id: str):
        """مسح سياق الجلسة"""
        if session_id in self.sessions:
            del self.sessions[session_id]

short_term_memory = ShortTermMemory()
