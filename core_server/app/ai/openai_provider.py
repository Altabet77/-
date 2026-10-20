import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger("samir.ai.openai")


class OpenAICompatibleProvider(AIProvider):
    """
    مزود متوافق مع معايير OpenAI API (يشمل OpenAI الرسمي، vLLM، LocalAI، وغيرها).
    يدعم استدعاء الدوال والأدوات (Function Calling) والرؤية الحاسوبية (Vision).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_name: str = "openai",
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY or ""
        self.base_url = base_url or settings.OPENAI_BASE_URL or None
        self.model = model or settings.OPENAI_MODEL or "gpt-4o"
        self.provider_name = provider_name

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
        """تجهيز الرسائل ودعم الصور Base64 للرؤية الحاسوبية في OpenAI"""
        prepared = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            parts = msg.get("parts")

            # إذا كانت الرسالة تحوي مرفقات وسائط ورؤية (parts)
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
                                "detail": "auto",
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
                f"OpenAI API key is not configured. Please add OPENAI_API_KEY in .env or settings."
            )

        prepared_msgs = self._prepare_messages(messages)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": prepared_msgs,
            "temperature": temperature,
        }

        if tools and len(tools) > 0:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            logger.info(f"Calling OpenAI model '{self.model}' via {self.provider_name}")
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
                "provider": self.provider_name,
                "model": self.model,
            }
        except Exception as e:
            logger.error(f"OpenAI Provider error: {e}", exc_info=True)
            raise e


class OpenAIProvider(OpenAICompatibleProvider):
    """مزود OpenAI الرسمي بنماذج GPT-4o و GPT-4o-mini و o1"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url or settings.OPENAI_BASE_URL or None,
            model=model or settings.OPENAI_MODEL or "gpt-4o",
            provider_name="openai",
        )
