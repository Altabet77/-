import json
import logging
from typing import Dict, Any, List, Callable, Optional
from app.core.security import assess_tool_risk, get_confirmation_message, RiskLevel

logger = logging.getLogger("samir.tools")


class ToolRegistry:
    """سجل الأدوات المركزي — يتتبع جميع الأدوات المتاحة لسمير"""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}
        # تتبع الأوامر المعلقة التي تنتظر تأكيد المستخدم
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable] = None,
    ):
        """تسجيل أداة بصيغة OpenAI Tool Schema"""
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._tools[name] = schema
        if handler:
            self._handlers[name] = handler
        logger.info(f"Registered tool: {name}")

    def register(
        self,
        name: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
        func: Optional[Callable] = None,
        schema: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Flexible register method supporting both schema dict and explicit params"""
        actual_handler = handler or func
        if schema:
            desc = schema.get("description", description or "")
            params = schema.get("parameters", parameters or {})
            tool_name = schema.get("name", name)
            return self.register_tool(name=tool_name, description=desc, parameters=params, handler=actual_handler)
        else:
            return self.register_tool(name=name, description=description or "", parameters=parameters or {}, handler=actual_handler)

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """جلب جميع الـ Schemas لتمريرها إلى الذكاء الاصطناعي"""
        return list(self._tools.values())

    def get_core_tool_schemas(self) -> List[Dict[str, Any]]:
        """جلب الأدوات الأساسية فقط لتسريع الاستجابة وتفادي حدود Groq Rate Limit"""
        core_names = {
            "generate_image", "execute_code", "search_youtube", "play_spotify", "open_browser_tab",
            "deep_learn_topic", "get_learned_knowledge", "query_knowledge_network",
            "save_correction", "get_learned_lessons", "set_voice", "set_speech_speed",
            "antigravity_list_skills", "antigravity_read_skill", "antigravity_get_status",
            "modify_file_content", "create_task", "list_tasks",
            "open_application", "open_file_or_folder", "read_file", "write_or_edit_file",
            "manage_filesystem", "control_volume", "system_power_control",
            "take_screenshot", "mouse_control", "keyboard_control", "execute_command",
            "web_search", "get_time",
            "create_web_project", "list_web_projects", "update_web_project", "launch_game",
            "inspect_url", "browser_navigate", "browser_get_page_text", "send_notification",
            "read_clipboard", "write_clipboard",
        }
        filtered = [s for name, s in self._tools.items() if name in core_names]
        return filtered if filtered else list(self._tools.values())

    def store_pending_confirmation(
        self, confirmation_id: str, tool_name: str, arguments: Dict[str, Any]
    ) -> None:
        """حفظ أمر ينتظر تأكيد المستخدم"""
        self._pending_confirmations[confirmation_id] = {
            "tool_name": tool_name,
            "arguments": arguments,
        }

    def pop_pending_confirmation(
        self, confirmation_id: str
    ) -> Optional[Dict[str, Any]]:
        """استرداد أمر معلق وحذفه من القائمة"""
        return self._pending_confirmations.pop(confirmation_id, None)

    def get_pending_confirmations(self) -> Dict[str, Dict[str, Any]]:
        """جلب جميع الأوامر المعلقة"""
        return dict(self._pending_confirmations)

    async def execute_tool(
        self, name: str, arguments: Dict[str, Any], bypass_confirmation: bool = False
    ) -> Dict[str, Any]:
        """
        تنفيذ الأداة بعد التحقق من مستوى الأمان.

        - LOW / MEDIUM  → تنفيذ مباشر
        - HIGH          → إرجاع needs_confirmation (ما لم يكن bypass_confirmation=True)
        - BLOCKED       → رفض تلقائي
        """
        risk = assess_tool_risk(name, arguments)
        logger.info(
            f"Tool '{name}' | risk={risk.value} | bypass={bypass_confirmation} | args={arguments}"
        )

        # ── BLOCKED ─────────────────────────────────────────────────────
        if risk == RiskLevel.BLOCKED:
            return {
                "status": "blocked",
                "risk_level": risk.value,
                "message": "هذا الأمر محظور أمنياً ولا يمكن تنفيذه.",
            }

        # ── HIGH → يحتاج تأكيد ─────────────────────────────────────────
        if risk == RiskLevel.HIGH and not bypass_confirmation:
            confirmation_msg = get_confirmation_message(name, arguments)
            import uuid
            confirmation_id = str(uuid.uuid4())[:8]
            self.store_pending_confirmation(confirmation_id, name, arguments)
            return {
                "status": "needs_confirmation",
                "risk_level": risk.value,
                "confirmation_id": confirmation_id,
                "message": confirmation_msg,
                "tool_name": name,
                "arguments": arguments,
            }

        # ── LOW / MEDIUM → تنفيذ مباشر ─────────────────────────────────
        if name in self._handlers:
            try:
                result = await self._handlers[name](**arguments)
                # أعد النتيجة مباشرة وأضف risk_level فقط (بدون تغليف إضافي يُربك الـ AI)
                if isinstance(result, dict):
                    result.setdefault("risk_level", risk.value)
                    return result
                return {
                    "status": "success",
                    "risk_level": risk.value,
                    "output": result,
                }
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                return {
                    "status": "error",
                    "risk_level": risk.value,
                    "message": str(e),
                }

        # لا يوجد handler محلي — يُمرَّر للـ PC Agent أو جهاز آخر
        return {
            "status": "forwarded_to_agent",
            "risk_level": risk.value,
            "tool": name,
            "arguments": arguments,
            "message": f"تم تجهيز أمر '{name}' لإرساله للجهاز المختص.",
        }

    async def confirm_and_execute(
        self, confirmation_id: str
    ) -> Dict[str, Any]:
        """تأكيد وتنفيذ أمر كان ينتظر الموافقة"""
        pending = self.pop_pending_confirmation(confirmation_id)
        if not pending:
            return {
                "status": "error",
                "message": f"لم أجد أمراً بالمعرف '{confirmation_id}'. ربما انتهت صلاحيته.",
            }
        return await self.execute_tool(
            pending["tool_name"], pending["arguments"], bypass_confirmation=True
        )

    async def reject_confirmation(self, confirmation_id: str) -> Dict[str, Any]:
        """رفض تنفيذ أمر كان ينتظر الموافقة"""
        pending = self.pop_pending_confirmation(confirmation_id)
        if not pending:
            return {"status": "error", "message": "لم أجد أمراً معلقاً بهذا المعرف."}
        return {
            "status": "rejected",
            "message": f"تم إلغاء تنفيذ '{pending['tool_name']}'.",
            "tool_name": pending["tool_name"],
        }


tool_registry = ToolRegistry()
