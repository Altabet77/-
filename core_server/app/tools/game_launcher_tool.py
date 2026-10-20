"""
game_launcher_tool.py — أداة تشغيل وإطلاق الألعاب لمساعد سمير
يمكّن سمير من تشغيل أي لعبة يصنعها (بايثون / Pygame / Turtle / ألعاب الويب)
في نافذة تفاعلية منبثقة حقيقية على سطح المكتب فوراً.
"""

import os
import re
import sys
import time
import logging
import py_compile
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.game_launcher")

# مسارات الألعاب ومفسر بايثون
CORE_DIR = Path(__file__).resolve().parent.parent.parent
GAMES_DIR = Path("d:/سمير/data/games").resolve()
GAMES_DIR.mkdir(parents=True, exist_ok=True)

VENV_PYTHON = CORE_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

PROJECTS_DIR = CORE_DIR / "projects"


def search_for_game_file(query: str) -> Optional[Path]:
    """البحث الذكي عن ملف لعبة بالاسم أو المسار"""
    # 1. فحص إذا كان المسار مباشراً وصحيحاً
    p = Path(query).expanduser()
    if p.exists() and p.is_file():
        return p.resolve()

    # 2. فحص مسارات شائعة في التنزيلات أو سطح المكتب
    search_dirs = [
        GAMES_DIR,
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        PROJECTS_DIR,
        Path("d:/سمير"),
    ]

    clean_q = query.lower().strip()
    # إزالة اللواحق الشائعة
    for word in ["لعبة", "game", "شغل", "play", "run", "افتح"]:
        clean_q = clean_q.replace(word, "").strip()

    # بحث مباشر مع .py
    target_names = [
        f"{clean_q}.py",
        f"{clean_q}_game.py",
        f"game_{clean_q}.py",
        clean_q if clean_q.endswith(".py") else f"{clean_q}.py",
    ]

    # مطابقة الأسماء العربية للإنجليزية
    alias_map = {
        "ثعبان": "snake",
        "الثعبان": "snake",
        "تتريس": "tetris",
        "ماريو": "mario",
        "بونغ": "pong",
        "فضاء": "space",
        "سباق": "race",
    }
    for ar_word, en_word in alias_map.items():
        if ar_word in query.lower():
            target_names.extend([f"{en_word}.py", f"{en_word}_game.py", f"game_{en_word}.py"])

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for t_name in target_names:
            candidate = s_dir / t_name
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()

        # فحص جزئي لكل الملفات
        try:
            for item in s_dir.glob("*.py"):
                if clean_q and (clean_q in item.name.lower()):
                    return item.resolve()
        except Exception:
            pass

    return None


async def tool_launch_game(
    game_name_or_path: str,
    code: Optional[str] = None,
    game_type: Optional[str] = "auto",
) -> Dict[str, Any]:
    """
    تشغيل لعبة وإطلاقها في نافذة حقيقية تفاعلية منبثقة أمام المستخدم (Pygame, Turtle, Tkinter أو ألعاب الويب).
    """
    try:
        # 1. إذا تم تقديم كود جديد للعبة، نقوم بحفظه أولاً
        if code and code.strip():
            clean_name = re.sub(r'[^a-zA-Z0-9_\u0600-\u06FF]', '_', game_name_or_path.strip()) or "game"
            if not clean_name.endswith(".py"):
                clean_name += ".py"

            file_path = GAMES_DIR / clean_name
            file_path.write_text(code, encoding="utf-8")
            target_file = file_path
            logger.info(f"Saved new game code to: {target_file}")
        else:
            # 2. البحث عن الملف الموجود
            target_file = search_for_game_file(game_name_or_path)

        if not target_file or not target_file.exists():
            # فحص إذا كانت لعبة ويب في مشاريع سمير
            if PROJECTS_DIR.exists():
                for p_dir in PROJECTS_DIR.iterdir():
                    if p_dir.is_dir():
                        meta_file = p_dir / "meta.json"
                        if meta_file.exists():
                            import json
                            try:
                                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                                if game_name_or_path.lower() in meta.get("name", "").lower() or game_name_or_path == meta.get("id", ""):
                                    # إطلاق لعبة ويب
                                    url = f"http://localhost:8000/projects/{meta.get('id')}/index.html"
                                    webbrowser.open(url)
                                    return {
                                        "status": "success",
                                        "game_type": "web",
                                        "name": meta.get("name"),
                                        "url": url,
                                        "message": f"🎮 تم فتح وتشغيل لعبة الويب «{meta.get('name')}» في المتصفح والواجهة بنجاح!",
                                    }
                            except Exception:
                                pass

            return {
                "status": "error",
                "message": f"لم يتم العثور على ملف اللعبة «{game_name_or_path}». تأكد من اسم اللعبة أو اكتب كودها لحفظها وتشغيلها.",
            }

        # 3. إذا كان ملف بايثون (.py)
        if target_file.suffix.lower() == ".py":
            # التحقق من صحة الكود وسلامة السنتكس
            try:
                py_compile.compile(str(target_file), doraise=True)
            except py_compile.PyCompileError as pe:
                logger.error(f"Syntax error in game script {target_file}: {pe}")
                return {
                    "status": "syntax_error",
                    "file": str(target_file),
                    "message": f"يوجد خطأ نحوي (SyntaxError) في كود اللعبة: {pe}",
                }

            # إطلاق اللعبة في نافذة مستقلة تفاعلية حقيقية
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP

            proc = subprocess.Popen(
                [str(VENV_PYTHON.resolve()), str(target_file.resolve())],
                cwd=str(target_file.parent.resolve()),
                creationflags=creation_flags,
                close_fds=True,
            )

            logger.info(f"Launched Python game '{target_file.name}' with PID {proc.pid}")

            return {
                "status": "success",
                "game_type": "python",
                "file_path": str(target_file.resolve()),
                "pid": proc.pid,
                "message": f"🎮🕹️ تم إطلاق وتشغيل اللعبة «{target_file.stem}» في نافذة تفاعلية منبثقة أمامك الآن على سطح المكتب! استمتع باللعب!",
            }

        # 4. إذا كان ملف HTML / ويب
        elif target_file.suffix.lower() in [".html", ".htm"]:
            webbrowser.open(f"file:///{target_file.resolve()}")
            return {
                "status": "success",
                "game_type": "html",
                "file_path": str(target_file.resolve()),
                "message": f"🎮 تم فتح وتشغيل اللعبة في نافذة المتصفح بنجاح!",
            }

        else:
            # استخدام فتح الملف الافتراضي
            os.startfile(str(target_file.resolve()))
            return {
                "status": "success",
                "file_path": str(target_file.resolve()),
                "message": f"تم تشغيل اللعبة: {target_file.name}",
            }

    except Exception as e:
        logger.error(f"Error launching game: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"تعذر تشغيل اللعبة: {e}",
        }


def register_game_launcher_tools():
    tool_registry.register_tool(
        name="launch_game",
        description="تشغيل وإطلاق أي لعبة يصنعها سمير أو يطلبها المستخدم (مثل ألعاب Pygame, Turtle, أو ألعاب الويب) في نافذة منبثقة تفاعلية حقيقية فوراً على الشاشة.",
        parameters={
            "type": "object",
            "properties": {
                "game_name_or_path": {
                    "type": "string",
                    "description": "اسم اللعبة (مثل: snake, الثعبان, تريس) أو مسار ملفها (مثل: c:/Users/Ziad/Downloads/snake_game.py)",
                },
                "code": {
                    "type": "string",
                    "description": "اختياري: كود اللعبة بالكامل إذا كنت تصنع لعبة بايثون جديدة لتشغيلها فوراً للمستخدم",
                },
                "game_type": {
                    "type": "string",
                    "enum": ["auto", "python", "web"],
                    "description": "نوع اللعبة (تلقائي، بايثون، أو ويب)",
                },
            },
            "required": ["game_name_or_path"],
        },
        handler=tool_launch_game,
    )


# تسجيل الأداة تلقائياً عند الاستيراد
register_game_launcher_tools()
