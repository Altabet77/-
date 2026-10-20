import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.code_runner")

PROJECT_SANDBOX_DIR = Path("./data/sandbox")
PROJECT_SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


async def tool_execute_code(language: str, code: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """
    تنفيذ كود برمجي (Python, PowerShell, JavaScript/Node) وإرجاع المخرجات فوراً للمستخدم.
    """
    lang = language.strip().lower()
    start_time = time.time()
    logger.info(f"Executing code [{lang}]:\n{code[:150]}...")

    try:
        if lang in ("python", "py"):
            # إذا كان الكود لعبة أو واجهة تفاعلية (Pygame, Turtle, Tkinter)
            is_gui = any(kw in code for kw in ["pygame", "turtle", "tkinter", "Tk()", "mainloop", "plt.show()", "cv2.imshow"])
            if is_gui:
                game_file = PROJECT_SANDBOX_DIR / f"game_{int(time.time())}.py"
                game_file.write_text(code, encoding="utf-8")
                creation_flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                proc = subprocess.Popen(
                    [sys.executable, str(game_file.resolve())],
                    cwd=str(PROJECT_SANDBOX_DIR.resolve()),
                    creationflags=creation_flags,
                    close_fds=True,
                )
                return {
                    "status": "success",
                    "output": f"تم إطلاق وتشغيل نافذة اللعبة التفاعلية بنجاح على سطح المكتب (PID: {proc.pid})! 🎮",
                    "pid": proc.pid,
                    "file_path": str(game_file.resolve()),
                    "language": "python",
                    "is_gui_game": True,
                    "message": "انطلقت نافذة اللعبة أمامك الآن لتلعب بها!",
                }

            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
            stdout = proc.stdout
            stderr = proc.stderr
            code_rc = proc.returncode

        elif lang in ("powershell", "ps1", "shell", "cmd"):
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", code],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
            stdout = proc.stdout
            stderr = proc.stderr
            code_rc = proc.returncode

        elif lang in ("javascript", "js", "node"):
            # Check if node exists
            proc = subprocess.run(
                ["node", "-e", code],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
            stdout = proc.stdout
            stderr = proc.stderr
            code_rc = proc.returncode

        elif lang in ("html", "web"):
            # Save to sandbox and return preview URL
            filename = f"preview_{int(time.time())}.html"
            preview_path = PROJECT_SANDBOX_DIR / filename
            with open(preview_path, "w", encoding="utf-8") as f:
                f.write(code)
            return {
                "status": "success",
                "message": "تم إنشاء صفحة الويب بنجاح.",
                "preview_url": f"/media/sandbox/{filename}",
                "execution_time": round(time.time() - start_time, 3),
                "code": code,
                "language": lang,
            }

        else:
            return {
                "status": "error",
                "message": f"لغة البرمجة '{language}' غير مدعومة حالياً. اللغات المدعومة: python, powershell, javascript, html",
            }

        elapsed = round(time.time() - start_time, 3)
        is_success = (code_rc == 0)

        output_text = stdout.strip() if stdout.strip() else (stderr.strip() if stderr.strip() else "تم التنفيذ بنجاح دون مخرجات.")

        return {
            "status": "success" if is_success else "failed",
            "output": output_text,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "return_code": code_rc,
            "execution_time": elapsed,
            "language": lang,
            "code": code,
            "message": f"تم تنفيذ كود {lang} في {elapsed} ثانية." if is_success else f"حدث خطأ أثناء تنفيذ الكود: {stderr.strip()[:200]}",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": f"استغرق الكود أكثر من {timeout_seconds} ثانية وتم إيقافه لسلامة النظام.",
            "execution_time": timeout_seconds,
        }
    except Exception as e:
        logger.error(f"Code runner error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"فشل تشغيل الكود: {e}",
        }


async def tool_create_code_file(filename: str, content: str, folder: Optional[str] = None) -> Dict[str, Any]:
    """
    إنشاء أو حفظ ملف برمجي جديد على الجهاز للمستخدم.
    """
    try:
        base = Path(folder) if folder else PROJECT_SANDBOX_DIR
        base.mkdir(parents=True, exist_ok=True)
        target_path = base / filename

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "message": f"تم إنشاء الملف البرمجي بنجاح: {filename}",
            "file_path": str(target_path.resolve()),
            "size_bytes": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {"status": "error", "message": f"تعذر إنشاء الملف: {e}"}


def register_code_runner_tools():
    tool_registry.register_tool(
        name="execute_code",
        description="كتابة وتشغيل كود برمجي (Python, JavaScript, PowerShell, HTML) وتجربته فوراً ورؤية النتائج للمستخدم.",
        parameters={
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": ["python", "powershell", "javascript", "html"],
                    "description": "لغة البرمجة المراد تنفيذها",
                },
                "code": {
                    "type": "string",
                    "description": "الكود البرمجي الكامل المطلوب تشغيله",
                },
            },
            "required": ["language", "code"],
        },
        handler=tool_execute_code,
    )

    tool_registry.register_tool(
        name="create_code_file",
        description="إنشاء ملف برمجي أو سكريبت وحفظه على الجهاز للمستخدم.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "اسم الملف مثل script.py أو app.js"},
                "content": {"type": "string", "description": "محتوى الكود المطلوب كتابته بالملف"},
                "folder": {"type": "string", "description": "المجلد الهدف (اختياري)"},
            },
            "required": ["filename", "content"],
        },
        handler=tool_create_code_file,
    )


register_code_runner_tools()
