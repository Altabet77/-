import json
import logging
from typing import List, Dict, Any, Optional
import anthropic
from app.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger("samir.ai.claude")


class ClaudeProvider(AIProvider):
    """
    مزود ذكاء اصطناعي لشركة Anthropic (عائلة نماذج Claude: Sonnet, Haiku, Opus).
    يدعم استدعاء الأدوات المتقدمة (Tool Use) والرؤية الحاسوبية وقراءة المستندات.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY or settings.CLAUDE_API_KEY or ""
        self.model = model or settings.CLAUDE_MODEL or "claude-3-5-sonnet-20241022"
        self.provider_name = "claude"

        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """تحويل مواصفات الأدوات من معيار OpenAPI/OpenAI إلى معيار Anthropic Claude"""
        claude_tools = []
        for t in tools:
            fn = t.get("function", t)
            name = fn.get("name")
            desc = fn.get("description", "")
            params = fn.get("parameters") or {"type": "object", "properties": {}}

            if not name:
                continue

            claude_tools.append({
                "name": name,
                "description": desc,
                "input_schema": params,
            })
        return claude_tools

    def _format_messages_for_claude(
        self,
        messages: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        فصل System Prompt عن باقي الرسائل، وتنسيق وسائط الصور واستدعاءات الأدوات لـ Claude.
        """
        system_prompt = ""
        claude_msgs: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            # 1. تجميع رسائل النظام لـ Claude
            if role == "system":
                if system_prompt:
                    system_prompt += "\n\n" + str(content)
                else:
                    system_prompt = str(content)
                continue

            # 2. نتائج استدعاء الأدوات (Tool results)
            if role == "tool":
                tool_id = msg.get("tool_call_id") or "tool_call"
                tool_result_content = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                
                # في Anthropic، ترسل نتائج الأدوات ضمن رسالة user مع block من نوع tool_result
                tool_block = {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": tool_result_content,
                }
                
                # إذا كانت الرسالة السابقة في القائمة من نوع user، ندمجها معها
                if claude_msgs and claude_msgs[-1]["role"] == "user":
                    prev_c = claude_msgs[-1]["content"]
                    if isinstance(prev_c, list):
                        prev_c.append(tool_block)
                    else:
                        claude_msgs[-1]["content"] = [{"type": "text", "text": str(prev_c)}, tool_block]
                else:
                    claude_msgs.append({
                        "role": "user",
                        "content": [tool_block]
                    })
                continue

            # 3. ردود المساعد التي قد تحتوي على Tool Calls سابقة
            if role == "assistant":
                blocks: List[Dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": str(content)})

                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    t_fn = tc.get("function", {})
                    t_name = t_fn.get("name") or tc.get("name")
                    t_id = tc.get("id") or t_name
                    t_args = t_fn.get("arguments") or tc.get("arguments") or {}
                    if isinstance(t_args, str):
                        try:
                            t_args = json.loads(t_args)
                        except Exception:
                            t_args = {"raw": t_args}

                    blocks.append({
                        "type": "tool_use",
                        "id": t_id,
                        "name": t_name,
                        "input": t_args,
                    })

                claude_msgs.append({
                    "role": "assistant",
                    "content": blocks if blocks else [{"type": "text", "text": ""}]
                })
                continue

            # 4. رسائل المستخدم (مع دعم الرؤية الحاسوبية Multimodal)
            parts = msg.get("parts")
            if parts and isinstance(parts, list):
                content_blocks: List[Dict[str, Any]] = []
                for p in parts:
                    if "inlineData" in p:
                        mime = p["inlineData"].get("mimeType", "image/jpeg")
                        data_b64 = p["inlineData"].get("data", "")
                        # Claude يدعم صور: image/jpeg, image/png, image/gif, image/webp
                        if mime.startswith("image/"):
                            content_blocks.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime,
                                    "data": data_b64,
                                }
                            })
                    elif "text" in p:
                        content_blocks.append({"type": "text", "text": p["text"]})

                claude_msgs.append({
                    "role": "user",
                    "content": content_blocks if content_blocks else [{"type": "text", "text": str(content)}]
                })
            else:
                claude_msgs.append({
                    "role": "user",
                    "content": [{"type": "text", "text": str(content)}]
                })

        # التأكد من عدم وجود رسائل متتالية بنفس الدور (Claude يتطلب تناوب user/assistant)
        normalized_msgs: List[Dict[str, Any]] = []
        for m in claude_msgs:
            if not normalized_msgs:
                normalized_msgs.append(m)
            elif normalized_msgs[-1]["role"] == m["role"]:
                # دمج المحتوى مع الرسالة السابقة
                prev_content = normalized_msgs[-1]["content"]
                curr_content = m["content"]
                if isinstance(prev_content, list) and isinstance(curr_content, list):
                    prev_content.extend(curr_content)
                elif isinstance(prev_content, str) and isinstance(curr_content, str):
                    normalized_msgs[-1]["content"] = prev_content + "\n" + curr_content
                else:
                    normalized_msgs.append(m)
            else:
                normalized_msgs.append(m)

        # التأكد من أن أول رسالة تبدأ بـ user
        if normalized_msgs and normalized_msgs[0]["role"] != "user":
            normalized_msgs.insert(0, {"role": "user", "content": [{"type": "text", "text": "مرحباً"}]})

        return system_prompt, normalized_msgs

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.6,
    ) -> Dict[str, Any]:
        """توليد رد من Anthropic Claude"""
        if not self.is_configured():
            raise RuntimeError(
                "Claude API key is not configured. Please add ANTHROPIC_API_KEY in .env or settings."
            )

        system_prompt, formatted_msgs = self._format_messages_for_claude(messages)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": formatted_msgs,
        }
        # بعض إصدارات anthropic SDK وموديلات Sonnet لا تقبل temperature كـ keyword argument
        # لذلك نتركه للإعداد الافتراضي الآمن لمنع TypeError

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools and len(tools) > 0:
            kwargs["tools"] = self._convert_tools(tools)

        try:
            logger.info(f"Calling Claude model: {self.model}")
            response = await self.client.messages.create(**kwargs)

            text_parts = []
            parsed_tool_calls = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    parsed_tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input if isinstance(block.input, dict) else json.loads(block.input),
                    })

            full_text = "\n".join(text_parts).strip()

            return {
                "content": full_text,
                "tool_calls": parsed_tool_calls,
                "provider": "claude",
                "model": self.model,
            }

        except Exception as e:
            logger.error(f"Claude Provider error: {e}", exc_info=True)
            raise e
