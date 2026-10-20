import json
import logging
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from app.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger("samir.ai.groq")

class GroqProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_CHAT_MODEL
        # max_retries=0 prevents Groq SDK from sleeping 30-45s on 429
        self.client = AsyncGroq(api_key=self.api_key, max_retries=0) if self.api_key else None

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.5
    ) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("Groq API key is not configured.")

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1200,
        }

        if tools and len(tools) > 0:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0].message

            parsed_tool_calls = []
            if choice.tool_calls:
                for tc in choice.tool_calls:
                    parsed_tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                    })

            return {
                "content": choice.content or "",
                "tool_calls": parsed_tool_calls,
                "provider": "groq",
                "model": kwargs.get("model", self.model)
            }
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Groq primary call error: {err_str[:120]}")
            
            # Fast fallback if 429 rate limit or model error
            if "429" in err_str or "model_not_found" in err_str or "404" in err_str:
                # Try fallback model without heavy tools if needed
                fallback_model = "openai/gpt-oss-20b"
                logger.info(f"Retrying quickly with fallback {fallback_model} (no sleep)...")
                kwargs["model"] = fallback_model
                kwargs["max_tokens"] = 800
                # لا نحذف الأدوات أبداً — إذا كان TPM exhausted مع الأدوات، نرمي Exception
                # ليعالجها الـ orchestrator ويرسلها لمزود آخر أكثر موثوقية (Claude)
                if "tpm" in err_str.lower() or "token" in err_str.lower():
                    logger.warning("Groq TPM exhausted with tools — raising for orchestrator fallback to Claude/OpenAI")
                    raise e
                try:
                    response = await self.client.chat.completions.create(**kwargs)
                    choice = response.choices[0].message
                    parsed_tool_calls = []
                    if choice.tool_calls:
                        for tc in choice.tool_calls:
                            parsed_tool_calls.append({
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                            })
                    return {
                        "content": choice.content or "",
                        "tool_calls": parsed_tool_calls,
                        "provider": "groq",
                        "model": fallback_model
                    }
                except Exception as e2:
                    logger.error(f"Groq fallback model error: {e2}")
                    raise e2
            raise e
