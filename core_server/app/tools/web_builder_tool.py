"""
web_builder_tool.py — محرك إبداع سمير لبناء المواقع والألعاب
يمكّن سمير من إنشاء مشاريع HTML/CSS/JS كاملة، عرضها داخل الواجهة، واستضافتها محلياً.
"""

import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.web_builder")

# ── مجلد المشاريع الرئيسي ──────────────────────────────────────────────────
PROJECTS_BASE_DIR = Path("./projects")
PROJECTS_BASE_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  أدوات المشاريع
# ══════════════════════════════════════════════════════════════════════════════

async def tool_create_web_project(
    name: str,
    description: str,
    html: str,
    css: Optional[str] = "",
    js: Optional[str] = "",
    project_type: Optional[str] = "website",
) -> Dict[str, Any]:
    """
    إنشاء موقع ويب أو لعبة جديدة وحفظها كمشروع كامل.
    يُنشئ مجلد المشروع ويتضمن HTML وCSS وJS ويجعلها قابلة للمعاينة الفورية.
    """
    try:
        project_id = str(uuid.uuid4())[:8]
        project_dir = PROJECTS_BASE_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        # بناء صفحة HTML الكاملة إذا لم تكن تحتوي على <html>
        if "<html" not in html.lower():
            full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name}</title>
<style>
{css or ''}
</style>
</head>
<body>
{html}
<script>
{js or ''}
</script>
</body>
</html>"""
        else:
            # إذا كانت HTML كاملة، أضف CSS وJS إذا كانا منفصلين
            full_html = html
            if css and "<style" not in html:
                full_html = full_html.replace("</head>", f"<style>\n{css}\n</style>\n</head>")
            if js and "<script" not in html:
                full_html = full_html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")

        # حفظ الملفات
        (project_dir / "index.html").write_text(full_html, encoding="utf-8")
        if css:
            (project_dir / "style.css").write_text(css, encoding="utf-8")
        if js:
            (project_dir / "script.js").write_text(js, encoding="utf-8")

        # حفظ البيانات التعريفية
        meta = {
            "id": project_id,
            "name": name,
            "description": description,
            "type": project_type,  # website / game / tool / app
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "files": ["index.html"] + (["style.css"] if css else []) + (["script.js"] if js else []),
        }
        (project_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        preview_url = f"/projects/{project_id}/index.html"
        logger.info(f"Created web project '{name}' (id={project_id})")

        return {
            "status": "success",
            "project_id": project_id,
            "name": name,
            "type": project_type,
            "preview_url": preview_url,
            "message": f"✅ تم إنشاء {'اللعبة' if project_type == 'game' else 'الموقع'} «{name}» بنجاح! يمكنك معاينته الآن.",
            "action": "open_preview",
        }

    except Exception as e:
        logger.error(f"Error creating web project: {e}", exc_info=True)
        return {"status": "error", "message": f"فشل إنشاء المشروع: {e}"}


async def tool_list_web_projects(project_type: Optional[str] = None) -> Dict[str, Any]:
    """
    عرض قائمة بجميع المشاريع المحفوظة (مواقع وألعاب).
    يمكن تصفيتها حسب النوع: website أو game أو tool.
    """
    try:
        projects: List[Dict] = []
        for folder in sorted(PROJECTS_BASE_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            meta_file = folder / "meta.json"
            if folder.is_dir() and meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    if project_type and meta.get("type") != project_type:
                        continue
                    meta["preview_url"] = f"/projects/{folder.name}/index.html"
                    projects.append(meta)
                except Exception:
                    pass

        return {
            "status": "success",
            "count": len(projects),
            "projects": projects,
            "message": f"لديك {len(projects)} {'مشروع' if len(projects) != 1 else 'مشاريع'} محفوظة.",
        }
    except Exception as e:
        return {"status": "error", "message": f"تعذر جلب المشاريع: {e}"}


async def tool_get_web_project(project_id: str) -> Dict[str, Any]:
    """
    جلب تفاصيل مشروع معين بما في ذلك الكود الكامل.
    """
    try:
        project_dir = PROJECTS_BASE_DIR / project_id
        if not project_dir.exists():
            return {"status": "error", "message": f"لم أجد مشروعاً بالمعرف '{project_id}'."}

        meta_file = project_dir / "meta.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

        html_content = ""
        css_content = ""
        js_content = ""

        if (project_dir / "index.html").exists():
            html_content = (project_dir / "index.html").read_text(encoding="utf-8")
        if (project_dir / "style.css").exists():
            css_content = (project_dir / "style.css").read_text(encoding="utf-8")
        if (project_dir / "script.js").exists():
            js_content = (project_dir / "script.js").read_text(encoding="utf-8")

        return {
            "status": "success",
            "project_id": project_id,
            "meta": meta,
            "html": html_content,
            "css": css_content,
            "js": js_content,
            "preview_url": f"/projects/{project_id}/index.html",
        }
    except Exception as e:
        return {"status": "error", "message": f"فشل جلب المشروع: {e}"}


async def tool_update_web_project(
    project_id: str,
    html: Optional[str] = None,
    css: Optional[str] = None,
    js: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    تحديث مشروع ويب موجود — تعديل الكود أو الاسم أو الوصف.
    """
    try:
        project_dir = PROJECTS_BASE_DIR / project_id
        if not project_dir.exists():
            return {"status": "error", "message": f"لم أجد مشروعاً بالمعرف '{project_id}'."}

        meta_file = project_dir / "meta.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

        if name:
            meta["name"] = name
        if description:
            meta["description"] = description
        meta["updated_at"] = datetime.now().isoformat()

        if css is not None:
            (project_dir / "style.css").write_text(css, encoding="utf-8")
        if js is not None:
            (project_dir / "script.js").write_text(js, encoding="utf-8")

        if html is not None:
            # إعادة بناء الـ HTML الكامل
            css_content = css or ((project_dir / "style.css").read_text(encoding="utf-8") if (project_dir / "style.css").exists() else "")
            js_content = js or ((project_dir / "script.js").read_text(encoding="utf-8") if (project_dir / "script.js").exists() else "")

            if "<html" not in html.lower():
                full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{meta.get('name', 'مشروع')}</title>
<style>
{css_content}
</style>
</head>
<body>
{html}
<script>
{js_content}
</script>
</body>
</html>"""
            else:
                full_html = html
            (project_dir / "index.html").write_text(full_html, encoding="utf-8")

        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "status": "success",
            "project_id": project_id,
            "preview_url": f"/projects/{project_id}/index.html",
            "message": f"✅ تم تحديث المشروع «{meta.get('name', project_id)}» بنجاح!",
            "action": "open_preview",
        }
    except Exception as e:
        return {"status": "error", "message": f"فشل تحديث المشروع: {e}"}


async def tool_delete_web_project(project_id: str) -> Dict[str, Any]:
    """
    حذف مشروع ويب بشكل نهائي.
    """
    try:
        project_dir = PROJECTS_BASE_DIR / project_id
        if not project_dir.exists():
            return {"status": "error", "message": f"لم أجد مشروعاً بالمعرف '{project_id}'."}

        meta_file = project_dir / "meta.json"
        name = project_id
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            name = meta.get("name", project_id)

        shutil.rmtree(project_dir)
        logger.info(f"Deleted web project '{name}' (id={project_id})")

        return {
            "status": "success",
            "message": f"تم حذف المشروع «{name}» بنجاح.",
        }
    except Exception as e:
        return {"status": "error", "message": f"فشل حذف المشروع: {e}"}


# ══════════════════════════════════════════════════════════════════════════════
#  تسجيل الأدوات
# ══════════════════════════════════════════════════════════════════════════════

def register_web_builder_tools():
    tool_registry.register_tool(
        name="create_web_project",
        description=(
            "بناء موقع ويب أو لعبة تفاعلية كاملة (HTML + CSS + JavaScript) وحفظها كمشروع يمكن معاينته فوراً داخل سمير. "
            "استخدم هذه الأداة عندما يطلب المستخدم إنشاء موقع أو لعبة أو أداة ويب. "
            "الأنواع المدعومة: website (موقع), game (لعبة), tool (أداة), app (تطبيق). "
            "مثال: لعبة Snake، موقع تعريفي، آلة حاسبة، ساعة رقمية."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "اسم المشروع بالعربي أو الإنجليزي"},
                "description": {"type": "string", "description": "وصف قصير لما يفعله المشروع"},
                "html": {"type": "string", "description": "كود HTML الكامل للمشروع"},
                "css": {"type": "string", "description": "كود CSS للتصميم (اختياري)"},
                "js": {"type": "string", "description": "كود JavaScript للتفاعل (اختياري)"},
                "project_type": {
                    "type": "string",
                    "enum": ["website", "game", "tool", "app"],
                    "description": "نوع المشروع: website أو game أو tool أو app",
                },
            },
            "required": ["name", "description", "html"],
        },
        handler=tool_create_web_project,
    )

    tool_registry.register_tool(
        name="list_web_projects",
        description="عرض قائمة بجميع المشاريع المحفوظة (مواقع وألعاب وأدوات). يمكن تصفيتها بالنوع.",
        parameters={
            "type": "object",
            "properties": {
                "project_type": {
                    "type": "string",
                    "enum": ["website", "game", "tool", "app"],
                    "description": "تصفية حسب النوع (اختياري)",
                },
            },
            "required": [],
        },
        handler=tool_list_web_projects,
    )

    tool_registry.register_tool(
        name="get_web_project",
        description="جلب تفاصيل وكود مشروع محفوظ بالمعرف.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "معرف المشروع (8 أحرف)"},
            },
            "required": ["project_id"],
        },
        handler=tool_get_web_project,
    )

    tool_registry.register_tool(
        name="update_web_project",
        description="تحديث كود أو اسم أو وصف مشروع ويب موجود.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "معرف المشروع المراد تعديله"},
                "html": {"type": "string", "description": "الكود الجديد لـ HTML (اختياري)"},
                "css": {"type": "string", "description": "الكود الجديد لـ CSS (اختياري)"},
                "js": {"type": "string", "description": "الكود الجديد لـ JS (اختياري)"},
                "name": {"type": "string", "description": "الاسم الجديد للمشروع (اختياري)"},
                "description": {"type": "string", "description": "الوصف الجديد (اختياري)"},
            },
            "required": ["project_id"],
        },
        handler=tool_update_web_project,
    )

    tool_registry.register_tool(
        name="delete_web_project",
        description="حذف مشروع ويب نهائياً.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "معرف المشروع المراد حذفه"},
            },
            "required": ["project_id"],
        },
        handler=tool_delete_web_project,
    )

    logger.info("Web Builder tools registered ✅")


register_web_builder_tools()
