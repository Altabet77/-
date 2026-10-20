import json
import logging
from typing import List, Dict, Any, Optional
from app.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger("samir.ai.gemini")


class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL

    def _build_gemini_contents(self, messages: List[Dict[str, Any]]):
        """
        تحويل قائمة الرسائل من صيغة OpenAI إلى صيغة Gemini الصحيحة.
        يدعم:
          - رسائل user/assistant العادية
          - رسائل assistant التي تحتوي على tool_calls (functionCall)
          - رسائل tool (functionResponse)
        """
        contents = []
        system_instruction = None

        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "")
            content = msg.get("content", "") or ""

            # ── System ────────────────────────────────────────────────────────
            if role == "system":
                raw_parts = msg.get("parts") or [{"text": content}]
                sys_text_parts = [{"text": str(p["text"])} for p in raw_parts if isinstance(p, dict) and p.get("text")]
                if sys_text_parts:
                    system_instruction = {"parts": sys_text_parts}
                i += 1
                continue

            # ── User ──────────────────────────────────────────────────────────
            if role == "user":
                raw_parts = msg.get("parts") or ([{"text": content}] if content else [])
                normalized = []
                for p in raw_parts:
                    if isinstance(p, dict):
                        if p.get("text"):
                            normalized.append({"text": str(p["text"])})
                        elif "inlineData" in p:
                            normalized.append(p)
                        elif "inline_data" in p:
                            id_obj = p["inline_data"]
                            normalized.append({
                                "inlineData": {
                                    "mimeType": id_obj.get("mime_type") or id_obj.get("mimeType", "image/jpeg"),
                                    "data": id_obj.get("data", "")
                                }
                            })
                    elif isinstance(p, str):
                        normalized.append({"text": p})
                if not normalized:
                    normalized = [{"text": str(content)}]
                contents.append({"role": "user", "parts": normalized})
                i += 1
                continue

            # ── Assistant (may contain tool_calls) ────────────────────────────
            if role in ("assistant", "model"):
                tool_calls = msg.get("tool_calls", [])

                if tool_calls:
                    # رسالة الـ model مع function calls — تحويل لـ Gemini functionCall
                    parts = []
                    if content:
                        parts.append({"text": str(content)})
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name") or tc.get("name", "")
                        fn_args_raw = fn.get("arguments") or tc.get("arguments", {})
                        if isinstance(fn_args_raw, str):
                            try:
                                fn_args = json.loads(fn_args_raw)
                            except Exception:
                                fn_args = {}
                        else:
                            fn_args = fn_args_raw or {}
                        fc_dict = {
                            "name": fn_name,
                            "args": fn_args,
                        }
                        part_dict = {"functionCall": fc_dict}
                        ts = tc.get("thought_signature") or tc.get("thoughtSignature") or fn.get("thought_signature") or fn.get("thoughtSignature")
                        if ts:
                            part_dict["thoughtSignature"] = ts
                        parts.append(part_dict)
                    if not parts:
                        parts = [{"text": ""}]
                    contents.append({"role": "model", "parts": parts})

                    # الآن نجمع كل نتائج الأدوات التالية لهذه الرسالة في رسالة user واحدة
                    i += 1
                    tool_result_parts = []
                    while i < len(messages) and messages[i].get("role") == "tool":
                        tr = messages[i]
                        tr_content_raw = tr.get("content", "{}")
                        try:
                            tr_content = json.loads(tr_content_raw)
                        except Exception:
                            tr_content = {"result": str(tr_content_raw)}

                        # نحصل على اسم الأداة من tool_call_id أو من الـ tool_calls السابقة
                        tc_id = tr.get("tool_call_id", "")
                        fn_name_for_result = tc_id
                        for tc in tool_calls:
                            fn_obj = tc.get("function", {})
                            if tc.get("id") == tc_id or fn_obj.get("name") == tc_id:
                                fn_name_for_result = fn_obj.get("name") or tc.get("name", tc_id)
                                break

                        tool_result_parts.append({
                            "functionResponse": {
                                "name": fn_name_for_result or tc_id or "tool",
                                "response": {"result": tr_content}
                            }
                        })
                        i += 1

                    if tool_result_parts:
                        contents.append({"role": "user", "parts": tool_result_parts})
                else:
                    # رسالة model عادية بدون tool calls
                    text_parts = [{"text": str(content)}] if content else [{"text": ""}]
                    contents.append({"role": "model", "parts": text_parts})
                    i += 1
                continue

            # ── Tool (orphaned — نادر) ─────────────────────────────────────────
            if role == "tool":
                # إذا وصلنا هنا فهناك tool result بدون assistant message سابقة — نضيفها كـ user
                tr_content_raw = msg.get("content", "{}")
                try:
                    tr_content = json.loads(tr_content_raw)
                except Exception:
                    tr_content = {"result": str(tr_content_raw)}
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.get("tool_call_id", "tool"),
                            "response": {"result": tr_content}
                        }
                    }]
                })
                i += 1
                continue

            i += 1

        # ضمان ألا تنتهي المحادثة بـ model turn (Gemini يرفض ذلك)
        if contents and contents[-1].get("role") == "model":
            logger.warning("Gemini: conversation ends with model turn — adding empty user continuation.")
            contents.append({"role": "user", "parts": [{"text": "استمر"}]})

        return contents, system_instruction

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.6
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Gemini API key is not configured.")

        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        contents, system_instruction = self._build_gemini_contents(messages)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if tools and len(tools) > 0:
            function_declarations = []
            for t in tools:
                fn = t.get("function", t)
                decl = {
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {"type": "object", "properties": {}})
                }
                function_declarations.append(decl)
            payload["tools"] = [{"function_declarations": function_declarations}]

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)

            # فالباك تلقائي فائق السرعة بين النماذج النشطة والمتاحة
            fallback_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
            tried = {self.model_name}
            while resp.status_code in (404, 400, 429, 503) and len(tried) < len(fallback_models):
                err_text = resp.text or ""
                for fb in fallback_models:
                    if fb not in tried:
                        logger.warning(f"Gemini model {self.model_name} failed ({resp.status_code}) — trying {fb}")
                        self.model_name = fb
                        tried.add(fb)
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{fb}:generateContent?key={self.api_key}"
                        try:
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                break
                        except Exception:
                            continue
                else:
                    break

            if resp.status_code != 200:
                logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Gemini API returned {resp.status_code}: {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return {"content": "", "tool_calls": [], "provider": "gemini", "model": self.model_name}

            first_cand = candidates[0]
            parts = first_cand.get("content", {}).get("parts", [])
            text_out = "".join([p.get("text", "") for p in parts if "text" in p])

            parsed_tool_calls = []
            for p in parts:
                if "functionCall" in p:
                    fc = p["functionCall"]
                    ts = p.get("thoughtSignature") or fc.get("thoughtSignature") or p.get("thought_signature") or fc.get("thought_signature")
                    tc_dict = {
                        "id": fc.get("name", "call_gemini"),
                        "name": fc.get("name"),
                        "arguments": fc.get("args", {})
                    }
                    if ts:
                        tc_dict["thought_signature"] = ts
                    parsed_tool_calls.append(tc_dict)

            return {
                "content": text_out,
                "tool_calls": parsed_tool_calls,
                "provider": "gemini",
                "model": self.model_name
            }
