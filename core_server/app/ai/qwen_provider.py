import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger("samir.ai.qwen")


class QwenProvider(AIProvider):
    """
    مزود ذكاء اصطناعي لعائلة نماذج Qwen (علي بابا / كوين 2.5 و Qwen-Max و Qwen-VL).
    يدعم:
    1. الاتصال الرسمي عبر Alibaba Cloud DashScope API (متوافق مع معيار OpenAI).
    2. الاتصال السريع عبر Groq (Qwen 2.5 / Qwen 3.8) في حال توفر مفتاح Groq وعدم توفر مفتاح DashScope.
    3. استدعاء الدوال والأدوات (Function Calling) والرؤية الحاسوبية (Qwen-VL).
    """

    DEFAULT_DASHSCOPE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.QWEN_API_KEY or ""
        self.base_url = base_url or settings.QWEN_BASE_URL or self.DEFAULT_DASHSCOPE_URL
        self.model = model or settings.QWEN_MODEL or "qwen2.5-72b-instruct"
        self.provider_name = "qwen"
        self.backend = "dashscope"

        # إذا لم يُحدد مفتاح Qwen ولكن يوجد مفتاح Groq، نوفر Qwen عبر محرك Groq فائق السرعة
        if not self.api_key and settings.GROQ_API_KEY:
            logger.info("QWEN_API_KEY not set. Using Groq Qwen backend for lightning speed.")
            self.api_key = settings.GROQ_API_KEY
            self.base_url = "https://api.groq.com/openai/v1"
            self.model = "qwen/qwen3.8-27b" if "qwen" in settings.GROQ_CHAT_MODEL else "qwen/qwen3.8-27b"
            self.backend = "groq_qwen"

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        else:
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """تجهيز الرسائل والصور لـ Qwen / Qwen-VL"""
        prepared = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            parts = msg.get("parts")

            if parts and isinstance(parts, list):
                content_list = []
                for p in parts:
                    if "inlineData" in p:
                        mime = p["inlineData"].get("mimeType", "image/jpeg")
                        b64 = p["inlineData"].get("data", "")
                        content_list.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{b64}",
                            }
                        })
                    elif "text" in p:
                        content_list.append({
                            "type": "text",
                            "text": p["text"],
                        })
                prepared.append({
                    "role": role,
                    "content": content_list if content_list else content,
                })
            else:
                m_copy = dict(msg)
                if "parts" in m_copy:
                    del m_copy["parts"]
                prepared.append(m_copy)

        return prepared

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.6,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError(
                "Qwen API key is not configured. Please add QWEN_API_KEY or GROQ_API_KEY in .env or settings."
            )

        prepared_msgs = self._prepare_messages(messages)

        # ضبط النموذج تلقائياً إذا كان هناك صور (Qwen-VL)
        has_images = any(
            isinstance(m.get("content"), list) and any(item.get("type") == "image_url" for item in m.get("content"))
            for m in prepared_msgs
        )

        chosen_model = self.model
        if has_images and self.backend == "dashscope":
            chosen_model = "qwen-vl-max"

        kwargs: Dict[str, Any] = {
            "model": chosen_model,
            "messages": prepared_msgs,
            "temperature": temperature,
        }

        if tools and len(tools) > 0 and not has_images:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            logger.info(f"Calling Qwen model '{chosen_model}' via {self.backend}")
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0].message

            parsed_tool_calls = []
            if choice.tool_calls:
                for tc in choice.tool_calls:
                    fn_args = tc.function.arguments
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {"raw": fn_args}

                    parsed_tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": fn_args,
                    })

            return {
                "content": choice.content or "",
                "tool_calls": parsed_tool_calls,
                "provider": "qwen",
                "model": chosen_model,
            }

        except Exception as e:
            logger.error(f"Qwen Provider error: {e}", exc_info=True)
            raise e
