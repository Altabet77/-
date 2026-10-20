import json
import logging
from typing import Dict, Any, Optional, List
import aiosqlite
from app.tools.base_tool import tool_registry
from app.core.config import settings

logger = logging.getLogger("samir.tools.modes")


async def tool_activate_mode(mode_name: str) -> Dict[str, Any]:
    """
    تفعيل وضع معين (Creator، Gaming، Work، Night).
    يجلب خطوات الوضع من قاعدة البيانات وينفذها.
    """
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM modes WHERE name = ? OR display_name LIKE ?",
            (mode_name.lower(), f"%{mode_name}%"),
        )
        mode = await cursor.fetchone()

    if not mode:
        return {
            "activated": False,
            "message": f"ما لقيت وضع باسم '{mode_name}'. الأوضاع المتاحة: creator, gaming, work, night",
        }

    mode_dict = dict(mode)
    steps_raw = mode_dict.get("steps", "[]")

    try:
        steps: List[Dict] = json.loads(steps_raw)
    except json.JSONDecodeError:
        return {
            "activated": False,
            "message": f"خطأ في إعدادات وضع '{mode_name}'.",
        }

    # تنفيذ كل خطوة وجمع النتائج
    from app.tools.base_tool import tool_registry as registry

    executed_steps = []
    for step in steps:
        tool_name = step.get("tool")
        tool_args = step.get("args", {})
        if not tool_name:
            continue

        result = await registry.execute_tool(tool_name, tool_args)
        executed_steps.append({
            "tool": tool_name,
            "args": tool_args,
            "status": result.get("status", "unknown"),
        })
        logger.info(f"Mode '{mode_name}' step: {tool_name} → {result.get('status')}")

    success_count = sum(1 for s in executed_steps if s["status"] in ("success", "forwarded_to_agent"))
    total = len(executed_steps)

    return {
        "activated": True,
        "mode": mode_dict["display_name"],
        "steps_executed": total,
        "steps_succeeded": success_count,
        "steps": executed_steps,
        "message": f"تم تفعيل {mode_dict['display_name']} — {success_count}/{total} خطوة نجحت.",
    }


async def tool_get_modes() -> Dict[str, Any]:
    """جلب قائمة الأوضاع المتاحة"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT name, display_name, description FROM modes ORDER BY id"
        )
        rows = await cursor.fetchall()
        modes = [dict(r) for r in rows]

    return {
        "modes": modes,
        "count": len(modes),
    }


async def tool_update_mode_steps(mode_name: str, steps_json: str) -> Dict[str, Any]:
    """
    تحديث خطوات وضع معين.
    steps_json: مصفوفة JSON تحتوي على خطوات الوضع.
    """
    try:
        # التحقق من صحة الـ JSON
        steps = json.loads(steps_json)
        if not isinstance(steps, list):
            return {"updated": False, "message": "steps_json يجب أن يكون مصفوفة JSON."}
    except json.JSONDecodeError as e:
        return {"updated": False, "message": f"خطأ في صيغة JSON: {e}"}

    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE modes SET steps=?, updated_at=CURRENT_TIMESTAMP WHERE name=?",
            (steps_json, mode_name.lower()),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return {"updated": False, "message": f"ما لقيت وضع باسم '{mode_name}'."}

    return {
        "updated": True,
        "mode": mode_name,
        "steps_count": len(steps),
        "message": f"تم تحديث خطوات وضع '{mode_name}' بنجاح.",
    }


def register_modes_tools():
    tool_registry.register_tool(
        name="activate_mode",
        description=(
            "تفعيل وضع عمل محدد مسبقاً. "
            "الأوضاع المتاحة: 'creator' (صانع المحتوى)، 'gaming' (الألعاب)، "
            "'work' (العمل)، 'night' (الليل). "
            "استخدم عندما يقول المستخدم 'فعّل وضع التصوير'، 'جهزلي بيئة الألعاب'، إلخ."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mode_name": {
                    "type": "string",
                    "description": "اسم الوضع المطلوب تفعيله (creator, gaming, work, night)",
                }
            },
            "required": ["mode_name"],
        },
        handler=tool_activate_mode,
    )

    tool_registry.register_tool(
        name="get_modes",
        description="جلب قائمة الأوضاع المتاحة وأوصافها.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=tool_get_modes,
    )

    tool_registry.register_tool(
        name="update_mode_steps",
        description=(
            "تحديث خطوات وضع معين. استخدم عندما يريد المستخدم تخصيص إجراءات وضع معين. "
            "يجب أن يكون steps_json مصفوفة JSON تحتوي على objects بالشكل: "
            '[{"tool": "tool_name", "args": {...}}]'
        ),
        parameters={
            "type": "object",
            "properties": {
                "mode_name": {
                    "type": "string",
                    "description": "اسم الوضع المراد تحديثه",
                },
                "steps_json": {
                    "type": "string",
                    "description": "خطوات الوضع الجديدة كـ JSON string",
                },
            },
            "required": ["mode_name", "steps_json"],
        },
        handler=tool_update_mode_steps,
    )


register_modes_tools()
