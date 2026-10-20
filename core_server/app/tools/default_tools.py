import datetime
from typing import Dict, Any
from app.tools.base_tool import tool_registry
from app.memory.long_term import long_term_memory

async def tool_save_memory(key: str, value: str, category: str = "general") -> Dict[str, Any]:
    """حفظ معلومة في الذاكرة الدائمة (خاصة بكل مستخدم مسجل عبر Google)"""
    res = await long_term_memory.save_fact(key, value, category)
    if isinstance(res, dict) and res.get("saved") is False:
        return res
    return {"saved": True, "fact": res}

async def tool_get_time() -> Dict[str, Any]:
    """معرفة الوقت والتاريخ الحالي"""
    now = datetime.datetime.now()
    return {
        "time": now.strftime("%I:%M %p"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A")
    }

async def tool_get_system_status() -> Dict[str, Any]:
    """معرفة حالة الأجهزة والأنظمة"""
    return {
        "status": "online",
        "cpu_usage": "18%",
        "ram_usage": "42%",
        "battery": "100%",
        "active_devices": ["Windows PC", "Android Client"]
    }

async def tool_set_voice(voice_or_dialect: str) -> Dict[str, Any]:
    """تغيير صوت سمير باختيار صوت واقعي من أصوات ElevenLabs (يدعم العربية والإنجليزية: آدم، ريتشل، برايان، بيلا، سارة، أنتوني، جوش، جورج، دانيال، ليلي، ليام، تشارلوت، تشارلي)"""
    from app.voice.tts_service import tts_service
    res = tts_service.set_voice(voice_or_dialect)
    return res

async def tool_set_speech_speed(speed: float) -> Dict[str, Any]:
    """تغيير سرعة نطق وإلقاء صوت سمير (1x, 2x, 3x, 4x, 5x)"""
    sp = max(1.0, min(5.0, round(float(speed), 1)))
    return {
        "status": "success",
        "action": "set_speech_speed",
        "speed": sp,
        "message": f"تم ضبط سرعة إلقاء صوت سمير على {sp}x بنجاح ⚡"
    }

def register_default_tools():
    # 1. الذاكرة
    tool_registry.register_tool(
        name="save_memory",
        description="حفظ معلومة مهمة صريحة أو تفضيل عن المستخدم في الذاكرة الدائمة عندما يطلب منك تذكر شيء أو يقدم حقيقة عن نفسه أو مشاريعه.",
        parameters={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "عنوان المعلومة باختصار (مثال: 'اسم مشروع اللعبة', 'المشروب المفضل')"
                },
                "value": {
                    "type": "string",
                    "description": "قيمة المعلومة أو تفاصيلها (مثال: 'Knight Quest')"
                },
                "category": {
                    "type": "string",
                    "enum": ["user_preference", "project", "personal", "general"],
                    "description": "تصنيف المعلومة"
                }
            },
            "required": ["key", "value"]
        },
        handler=tool_save_memory
    )

    # 2. الوقت والتاريخ
    tool_registry.register_tool(
        name="get_time",
        description="معرفة الوقت أو التاريخ الحالي.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=tool_get_time
    )

    # 3. حالة النظام
    tool_registry.register_tool(
        name="get_system_status",
        description="الاستعلام عن حالة الكمبيوتر والنظام والأجهزة المتصلة.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=tool_get_system_status
    )

    # 4. تغيير الصوت (ElevenLabs)
    tool_registry.register_tool(
        name="set_voice",
        description="تغيير صوت سمير التحدث به عبر أصوات ElevenLabs فائقة الواقعية (يدعم العربية والإنجليزية بطلاقة: 'آدم', 'ريتشل', 'برايان', 'بيلا', 'سارة', 'أنتوني', 'جوش', 'جورج', 'دانيال', 'ليلي', 'ليام', 'تشارلوت', 'تشارلي', 'عربي', 'إنجليزي').",
        parameters={
            "type": "object",
            "properties": {
                "voice_or_dialect": {
                    "type": "string",
                    "description": "اسم صوت ElevenLabs المطلوب (مثال: 'آدم' أو 'Adam', 'ريتشل' أو 'Rachel', 'برايان' أو 'Brian', 'سارة' أو 'Sarah', 'جورج' أو 'George')"
                }
            },
            "required": ["voice_or_dialect"]
        },
        handler=tool_set_voice
    )

    # 5. فتح رابط أو موقع
    tool_registry.register_tool(
        name="open_url",
        description="فتح موقع أو رابط ويب في المتصفح.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "الرابط أو اسم الموقع المطلوب فتحه (مثال: 'https://youtube.com' أو 'youtube')"
                }
            },
            "required": ["url"]
        }
    )

    # 6. التحكم بالصوت
    tool_registry.register_tool(
        name="control_volume",
        description="التحكم بمستوى صوت الكمبيوتر (رفع، خفض، كتم، أو تحديد نسبة مئوية).",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["up", "down", "mute", "unmute", "set"],
                    "description": "نوع الإجراء"
                },
                "level": {
                    "type": "integer",
                    "description": "مستوى الصوت بالنسبة المئوية (0-100) في حالة action='set'"
                }
            },
            "required": ["action"]
        }
    )

    # 7. إيقاف / إعادة تشغيل / قفل
    tool_registry.register_tool(
        name="system_power_control",
        description="التحكم بالطاقة (قفل الشاشة، النوم، إعادة التشغيل، إيقاف التشغيل).",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["lock", "sleep", "restart", "shutdown"],
                    "description": "إجراء الطاقة المطلوب"
                }
            },
            "required": ["action"]
        }
    )

    # 8. سرعة نطق وإلقاء صوت سمير (1x, 2x, 3x, 4x, 5x)
    tool_registry.register_tool(
        name="set_speech_speed",
        description="تغيير سرعة نطق وإلقاء صوت سمير (1x, 2x, 3x, 4x, 5x).",
        parameters={
            "type": "object",
            "properties": {
                "speed": {
                    "type": "number",
                    "description": "سرعة الكلام بالأرقام: 1.0 (عادي 1x), 2.0 (مضاعف 2x), 3.0 (سريع 3x), 4.0 (فائق 4x), 5.0 (صاروخي 5x)"
                }
            },
            "required": ["speed"]
        },
        handler=tool_set_speech_speed
    )

register_default_tools()
