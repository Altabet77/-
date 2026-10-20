from enum import Enum
from typing import Dict, Any, Optional

class RiskLevel(str, Enum):
    LOW = "LOW"             # فتح البرامج، تصفح، حالة الجهاز
    MEDIUM = "MEDIUM"       # إغلاق البرامج، كتم/تعديل الصوت، قفل الشاشة
    HIGH = "HIGH"           # حذف ملفات، إيقاف/إعادة تشغيل الكمبيوتر
    BLOCKED = "BLOCKED"     # أوامر Shell خطيرة وغير مقيدة

# خريطة الأدوات وتصنيف خطورتها
TOOL_RISK_MAP: Dict[str, RiskLevel] = {
    # أدوات منخفضة الخطورة — تنفذ تلقائيًا
    "get_system_status": RiskLevel.LOW,
    "open_application": RiskLevel.LOW,
    "open_url": RiskLevel.LOW,
    "search_files": RiskLevel.LOW,
    "get_weather": RiskLevel.LOW,
    "get_time": RiskLevel.LOW,
    "web_search": RiskLevel.LOW,
    "create_task": RiskLevel.LOW,
    "list_tasks": RiskLevel.LOW,
    "complete_task": RiskLevel.LOW,
    "activate_mode": RiskLevel.LOW,
    "get_modes": RiskLevel.LOW,
    "save_memory": RiskLevel.LOW,
    "get_memories": RiskLevel.LOW,

    # أدوات الوسائط، الرسم، التصفح، والتعلم الذاتي
    "generate_image": RiskLevel.LOW,
    "generate_ai_image": RiskLevel.LOW,
    "search_youtube": RiskLevel.LOW,
    "play_spotify": RiskLevel.LOW,
    "open_browser_tab": RiskLevel.LOW,
    "open_web_service": RiskLevel.LOW,
    "deep_learn_topic": RiskLevel.LOW,
    "get_learned_knowledge": RiskLevel.LOW,
    "save_correction": RiskLevel.LOW,
    "get_learned_lessons": RiskLevel.LOW,
    "create_code_file": RiskLevel.LOW,
    "execute_code": RiskLevel.LOW,
    "modify_file_content": RiskLevel.LOW,
    "query_knowledge_network": RiskLevel.LOW,
    "open_file_or_folder": RiskLevel.LOW,
    "read_file": RiskLevel.LOW,
    "write_or_edit_file": RiskLevel.LOW,
    "manage_filesystem": RiskLevel.MEDIUM,
    "execute_command": RiskLevel.MEDIUM,
    "take_screenshot": RiskLevel.LOW,
    "mouse_control": RiskLevel.LOW,
    "keyboard_control": RiskLevel.LOW,
    "antigravity_list_skills": RiskLevel.LOW,
    "antigravity_read_skill": RiskLevel.LOW,
    "antigravity_get_status": RiskLevel.LOW,
    "set_voice": RiskLevel.LOW,
    "set_speech_speed": RiskLevel.LOW,
    "create_web_project": RiskLevel.LOW,
    "launch_game": RiskLevel.LOW,

    # أدوات متوسطة الخطورة — قد تحتاج تأكيد
    "close_application": RiskLevel.MEDIUM,
    "control_volume": RiskLevel.LOW,
    "set_volume": RiskLevel.LOW,
    "media_control": RiskLevel.LOW,
    "delete_task": RiskLevel.MEDIUM,
    "cancel_task": RiskLevel.MEDIUM,

    # أدوات عالية الخطورة — تحتاج تأكيد صريح
    "system_power_control": RiskLevel.HIGH,
    "shutdown_pc": RiskLevel.HIGH,
    "restart_pc": RiskLevel.HIGH,
    "delete_file": RiskLevel.HIGH,
    "execute_script": RiskLevel.HIGH,
    "lock_pc": RiskLevel.HIGH,
    "format_drive": RiskLevel.BLOCKED,
}

BLOCKED_SHELL_PATTERNS = [
    "format", "rmdir /s", "del /f /s /q", "rm -rf", "drop database",
    "mkfs", "powershell -enc", "certutil -urlcache"
]

# رسائل تأكيد واضحة لكل أداة عالية الخطورة
CONFIRMATION_MESSAGES: Dict[str, str] = {
    "system_power_control": {
        "shutdown": "سأوقف تشغيل الكمبيوتر. متأكد؟",
        "restart": "سأعيد تشغيل الكمبيوتر. متأكد؟",
        "lock": "سأقفل شاشة الكمبيوتر. نكمل؟",
        "sleep": "سأضع الكمبيوتر في وضع النوم. متأكد؟",
    },
    "delete_file": "سأحذف الملف نهائياً. هذا الإجراء لا يمكن التراجع عنه. متأكد؟",
    "execute_script": "سأشغل سكريبت على الجهاز. متأكد من المتابعة؟",
}

def get_confirmation_message(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """إنشاء رسالة تأكيد واضحة ومحددة للمستخدم"""
    msg = CONFIRMATION_MESSAGES.get(tool_name)
    if isinstance(msg, dict) and arguments:
        action = arguments.get("action", "")
        return msg.get(action, f"سأنفذ '{tool_name}'. متأكد؟")
    if isinstance(msg, str):
        return msg
    return f"هذا الأمر عالي الخطورة. هل تريد تنفيذ '{tool_name}'؟"

def assess_tool_risk(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> RiskLevel:
    """تقييم مستوى خطورة استدعاء الأداة"""
    if tool_name not in TOOL_RISK_MAP:
        return RiskLevel.HIGH  # أي أداة غير معروفة تعتبر عالية الخطورة افتراضياً

    risk = TOOL_RISK_MAP[tool_name]

    # فحص إضافي للأوامر النصية والمصطلحات الخطرة
    if arguments:
        args_str = str(arguments).lower()
        for blocked in BLOCKED_SHELL_PATTERNS:
            if blocked in args_str:
                return RiskLevel.BLOCKED

    return risk
