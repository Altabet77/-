from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class AIProvider(ABC):
    """الواجهة الموحدة لجميع مزودي الذكاء الاصطناعي في سمير"""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.6
    ) -> Dict[str, Any]:
        """
        توليد رد من النموذج.
        الإرجاع عبارة عن قاموس يحتوي على:
        - "content": نص الرد (str أو None)
        - "tool_calls": قائمة استدعاءات الأدوات (List[Dict]) إن وجدت
        - "provider": اسم المزود المستخدم
        """
        pass
