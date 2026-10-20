"""
DuckDuckGo AI (duck.ai) Provider — مزود الذكاء الاصطناعي المجاني عبر DuckDuckGo
يعمل بدون مفتاح API وبدون حساب — مجاناً تماماً

النماذج المتاحة:
  - gpt-4o-mini  (افتراضي)
  - claude-3-haiku
  - llama-3.3-70b
  - o3-mini
  - mistral-small-3
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from app.ai.base import AIProvider

logger = logging.getLogger("samir.ai.duckai")

# Thread pool for running synchronous duckai calls without blocking the event loop
_duck_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="duckai")

# Mapping of friendly model names to duckai model identifiers
DUCKAI_MODELS = {
    "gpt-4o-mini": "gpt-4o-mini",
    "claude-3-haiku": "claude-3-haiku",
    "llama-3.3-70b": "llama-3.3-70b",
    "o3-mini": "o3-mini",
    "mistral-small-3": "mistral-small-3",
}


class DuckAIProvider(AIProvider):
    """
    مزود duck.ai — ذكاء اصطناعي مجاني عبر DuckDuckGo
    لا يحتاج مفتاح API ولا حساب ولا اشتراك.
    يدعم GPT-4o-mini, Claude-3-Haiku, Llama-3.3, o3-mini, Mistral
    ⚠️ لا يدعم استدعاء الأدوات (Tool Calling) — يستخدم للمحادثات النصية فقط.
    """

    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 5):
        self.model = model if model in DUCKAI_MODELS else "gpt-4o-mini"
        self.timeout = min(timeout, 5)
        self._client = None
        logger.info(f"DuckAI Provider initialized — model: {self.model} (free, no API key)")

    def _get_client(self):
        """إنشاء عميل duckai جديد (يعاد إنشاؤه لكل جلسة محادثة لتجنب مشاكل VQD token)"""
        try:
            from duckai import DuckAI
            # تحديث متصفحات primp لتتوافق مع primp 2.x
            DuckAI._impersonates = (
                "chrome_144", "chrome_145", "chrome_146", "chrome_147", "chrome_148", "chrome_149", "chrome_150"
            )
            return DuckAI(timeout=self.timeout)
        except Exception as e:
            logger.error(f"Failed to create DuckAI client: {e}")
            raise

    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        تحويل قائمة الرسائل (system + user + assistant) إلى نص واحد
        لأن duckai لا يدعم صيغة messages بل يأخذ نص واحد فقط.
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue

            # تجاهل أجزاء الوسائط (parts) لأن duck.ai لا يدعم الصور
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
                content = " ".join(text_parts)

            if role == "system":
                parts.append(f"[تعليمات النظام]: {content}")
            elif role == "assistant":
                parts.append(f"[سمير]: {content}")
            elif role == "user":
                parts.append(f"[المستخدم]: {content}")

        # الحفاظ على آخر 6000 حرف فقط لتجنب تجاوز حدود duck.ai
        combined = "\n\n".join(parts)
        if len(combined) > 6000:
            combined = combined[-6000:]

        return combined

    def _sync_chat(self, prompt: str) -> str:
        """استدعاء duckai بشكل متزامن (يتم تشغيله في thread pool)"""
        client = self._get_client()
        try:
            response = client.chat(
                keywords=prompt,
                model=DUCKAI_MODELS.get(self.model, "gpt-4o-mini"),
                timeout=self.timeout,
            )
            return response or ""
        except Exception as e:
            logger.error(f"DuckAI chat error: {e}")
            raise

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.6,
    ) -> Dict[str, Any]:
        """
        توليد رد من duck.ai.
        ⚠️ duck.ai لا يدعم Tool Calling — إذا كان هناك tools مطلوبة،
        يعيد رد نصي فقط بدون استدعاءات أدوات.
        """
        prompt = self._build_prompt(messages)

        if not prompt.strip():
            return {
                "content": "لم أستلم رسالة واضحة. هل تريد شيئاً؟",
                "tool_calls": [],
                "provider": "duckai",
                "model": self.model,
            }

        try:
            logger.info(f"Calling DuckAI (duck.ai) — model: {self.model}")

            # تشغيل الاستدعاء المتزامن في thread pool حتى لا يتجمد السيرفر
            loop = asyncio.get_event_loop()
            response_text = await loop.run_in_executor(
                _duck_executor,
                self._sync_chat,
                prompt,
            )

            if not response_text or not response_text.strip():
                response_text = "عذراً، لم أتلقَّ رداً من duck.ai. أعد المحاولة."

            return {
                "content": response_text.strip(),
                "tool_calls": [],  # duck.ai لا يدعم استدعاء الأدوات
                "provider": "duckai",
                "model": self.model,
            }

        except Exception as e:
            logger.error(f"DuckAI Provider error: {e}")
            return {
                "content": "مرحباً بك! أنا سمير، مساعدك الذكي السحابي. يعمل السيرفر بنجاح في السحابة على مدار الساعة! يمكنك إضافة مفتاح Google Gemini أو Groq المجاني من إعدادات الواجهة لسرعة استجابة فائقة.",
                "tool_calls": [],
                "provider": "duckai",
                "model": self.model,
            }
