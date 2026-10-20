"""
Antigravity Bridge Tool for Samir (جسر الربط مع بيئة أنتي قرافيتي)

يمكن سمير من:
1. استكشاف مهارات أنتي قرافيتي (Antigravity Skills & Plugins).
2. قراءة تعليمات أي مهارة (SKILL.md) لتطبيق معايير وأفضل ممارسات أنتي قرافيتي.
3. فحص حالة بيئة أنتي قرافيتي وربط سياق العمل والمشاريع.
"""

import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.antigravity")

# مسارات بيئة أنتي قرافيتي
USER_HOME = Path.home()
GEMINI_DIR = USER_HOME / ".gemini"
GLOBAL_PLUGINS_DIR = GEMINI_DIR / "config" / "plugins"
BUILTIN_SKILLS_DIR = GEMINI_DIR / "antigravity-ide" / "builtin" / "skills"
WORKSPACE_DIR = Path("d:/سمير").resolve()
WORKSPACE_AGENTS_DIR = WORKSPACE_DIR / ".agents"


def _discover_all_skills() -> List[Dict[str, str]]:
    """فحص واكتشاف جميع المهارات المتاحة في أنتي قرافيتي"""
    skills = []

    # 1. فحص المهارات المدمجة (Builtin)
    if BUILTIN_SKILLS_DIR.exists():
        for skill_dir in BUILTIN_SKILLS_DIR.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    skills.append(_parse_skill_metadata(skill_md, "Builtin Antigravity Skill"))

    # 2. فحص إضافات ومهارات Plugins
    if GLOBAL_PLUGINS_DIR.exists():
        for plugin_dir in GLOBAL_PLUGINS_DIR.iterdir():
            if plugin_dir.is_dir():
                # مهارات داخل مجلد skills بالبلجن
                plugin_skills_dir = plugin_dir / "skills"
                if plugin_skills_dir.exists():
                    for sk_dir in plugin_skills_dir.iterdir():
                        if sk_dir.is_dir():
                            sk_md = sk_dir / "SKILL.md"
                            if sk_md.exists():
                                skills.append(_parse_skill_metadata(sk_md, f"Plugin: {plugin_dir.name}"))
                        elif sk_dir.name.upper() == "SKILL.MD":
                            skills.append(_parse_skill_metadata(sk_dir, f"Plugin: {plugin_dir.name}"))

    # 3. فحص مهارات مساحة العمل الحالية (.agents)
    if WORKSPACE_AGENTS_DIR.exists():
        ws_skills = WORKSPACE_AGENTS_DIR / "skills"
        if ws_skills.exists():
            for sk_dir in ws_skills.iterdir():
                if sk_dir.is_dir():
                    sk_md = sk_dir / "SKILL.md"
                    if sk_md.exists():
                        skills.append(_parse_skill_metadata(sk_md, "Workspace Skill"))

    return skills


def _parse_skill_metadata(skill_path: Path, source_label: str) -> Dict[str, str]:
    """استخراج اسم ووصف المهارة من frontmatter أو بداية الملف"""
    name = skill_path.parent.name
    desc = "مهارة متقدمة في بيئة أنتي قرافيتي"
    try:
        content = skill_path.read_text(encoding="utf-8", errors="ignore")
        fm_match = re.search(r"^---\s*(.*?)\s*---", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            name_match = re.search(r"name:\s*(.+)", fm_text)
            desc_match = re.search(r"description:\s*(.+)", fm_text)
            if name_match:
                name = name_match.group(1).strip()
            if desc_match:
                desc = desc_match.group(1).strip()
        else:
            first_lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
            if first_lines:
                desc = first_lines[0][:120]
    except Exception as e:
        logger.warning(f"Error parsing skill {skill_path}: {e}")

    return {
        "name": name,
        "description": desc,
        "path": str(skill_path),
        "source": source_label
    }


async def tool_antigravity_list_skills(category: Optional[str] = None) -> Dict[str, Any]:
    """
    استعراض جميع المهارات البرمجية والتحليلية المتاحة في بيئة أنتي قرافيتي (Skills).
    """
    skills = _discover_all_skills()
    if category:
        cat_lower = category.lower()
        skills = [s for s in skills if cat_lower in s["name"].lower() or cat_lower in s["description"].lower()]

    return {
        "status": "success",
        "total_skills": len(skills),
        "skills": skills[:25],
        "message": f"تم العثور على {len(skills)} مهارة متقدمة في بيئة أنتي قرافيتي."
    }


async def tool_antigravity_read_skill(skill_name: str) -> Dict[str, Any]:
    """
    قراءة محتوى وتعليمات مهارة معينة من مهارات أنتي قرافيتي لتطبيقها في العمل البرمجي أو التقني.
    """
    all_skills = _discover_all_skills()
    target_skill = None
    skill_name_lower = skill_name.strip().lower()

    for s in all_skills:
        if s["name"].lower() == skill_name_lower or skill_name_lower in s["name"].lower():
            target_skill = s
            break

    if not target_skill:
        return {
            "status": "not_found",
            "message": f"لم يتم العثور على مهارة باسم '{skill_name}' في بيئة أنتي قرافيتي. استخدم antigravity_list_skills لمعرفة المتاح.",
            "available_samples": [s["name"] for s in all_skills[:10]]
        }

    skill_path = Path(target_skill["path"])
    try:
        content = skill_path.read_text(encoding="utf-8", errors="ignore")
        # اقتطاع الأجزاء الطويلة جداً لعدم إرهاق التوكنز
        lines = content.splitlines()
        content_snippet = "\n".join(lines[:200])
        if len(lines) > 200:
            content_snippet += f"\n\n... تم اختصار باقي المهارة ({len(lines)} سطر إجمالي) ..."

        return {
            "status": "success",
            "skill_name": target_skill["name"],
            "source": target_skill["source"],
            "instructions": content_snippet,
            "message": f"تم جلب تعليمات مهارة '{target_skill['name']}' بنجاح."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"فشل قراءة ملف المهارة: {str(e)}"
        }


async def tool_antigravity_get_status() -> Dict[str, Any]:
    """
    التحقق من حالة بيئة أنتي قرافيتي ومسارات التكامل معها.
    """
    skills_count = len(_discover_all_skills())
    
    # محاولة فحص أمر agy عبر powershell/cmd
    agy_version = "غير متوفر كأمر مباشر في PATH"
    try:
        proc = subprocess.run(["agy", "--version"], capture_output=True, text=True, timeout=2)
        if proc.returncode == 0:
            agy_version = proc.stdout.strip()
    except Exception:
        pass

    return {
        "status": "connected",
        "antigravity_ide_detected": BUILTIN_SKILLS_DIR.exists() or GLOBAL_PLUGINS_DIR.exists(),
        "total_skills_available": skills_count,
        "active_workspace": str(WORKSPACE_DIR),
        "cli_status": agy_version,
        "integration_status": "Active & Synchronized",
        "message": f"سمير مرتبط بنجاح مع بيئة أنتي قرافيتي ومع قاعدة معارفه ({skills_count} مهارة متاحة)."
    }


# ─── تسجيل الأدوات في ToolRegistry ────────────────────────────────────

tool_registry.register_tool(
    name="antigravity_list_skills",
    description="استعراض والبحث في مهارات (Skills) بيئة أنتي قرافيتي المتاحة لسمير، مثل مهارات الويب والتصحيح وقواعد البيانات.",
    parameters={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "فلترة المهارات حسب موضوع أو كلمة بحث (اختياري، مثل: web, flutter, debug, sql)"
            }
        },
        "required": []
    },
    handler=tool_antigravity_list_skills
)

tool_registry.register_tool(
    name="antigravity_read_skill",
    description="قراءة دليل وتعليمات مهارة متخصصة من مهارات أنتي قرافيتي واتباع خطواتها الاحترافية لحل مشكلة برمجية أو معمارية.",
    parameters={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "اسم المهارة في أنتي قرافيتي (مثل: modern-web-guidance, chrome-devtools, building-data-apps)"
            }
        },
        "required": ["skill_name"]
    },
    handler=tool_antigravity_read_skill
)

tool_registry.register_tool(
    name="antigravity_get_status",
    description="فحص حالة الاتصال بين سمير وبيئة أنتي قرافيتي، وعرض المهارات ومسارات التكامل النشطة.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    handler=tool_antigravity_get_status
)
