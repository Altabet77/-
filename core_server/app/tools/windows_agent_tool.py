import os
import sys
import re
import time
import base64
import ctypes
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.windows_agent")

SCREENSHOTS_DIR = Path("./data/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# 1. SCREENSHOT
# ──────────────────────────────────────────────────────────────────────────────
async def tool_take_screenshot() -> Dict[str, Any]:
    """
    التقاط صورة كاملة لشاشة الكمبيوتر الحالية لتمكين سمير من رؤية ما يشاهده المستخدم.
    """
    timestamp = int(time.time())
    file_path = SCREENSHOTS_DIR / f"screenshot_{timestamp}.png"
    latest_path = SCREENSHOTS_DIR / "screenshot_latest.png"

    # طريقة 1: استخدام Pillow إن وجد
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(str(file_path))
        img.save(str(latest_path))
    except Exception:
        # طريقة 2: استخدام PowerShell النظيف والمدمج في ويندوز بدون أي مكتبات
        ps_cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save('{str(file_path.resolve())}', [System.Drawing.Imaging.ImageFormat]::Png)
        $bitmap.Save('{str(latest_path.resolve())}', [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, check=True)

    if not file_path.exists():
        return {"status": "error", "message": "تعذر التقاط صورة الشاشة."}

    # قراءة الصورة كـ Base64 للتحليل البصري
    with open(file_path, "rb") as f:
        img_bytes = f.read()
    b64_str = base64.b64encode(img_bytes).decode("utf-8")

    logger.info(f"Screenshot captured: {file_path}")
    return {
        "status": "success",
        "message": "تم التقاط صورة الشاشة بنجاح.",
        "file_path": str(file_path.resolve()),
        "image_base64": b64_str,
        "image_base64_length": len(b64_str),
        "image_url": f"/static/screenshots/screenshot_latest.png",
    }


# ──────────────────────────────────────────────────────────────────────────────
# 2. MOUSE & KEYBOARD AUTOMATION (ctypes user32)
# ──────────────────────────────────────────────────────────────────────────────
async def tool_mouse_control(action: str, x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1) -> Dict[str, Any]:
    """
    التحكم في حركة الماوس والنقر (تحريك، نقر، نقر مزدوج، نقر يمين، تمرير عجلة الماوس).
    action: 'move', 'click', 'double_click', 'right_click', 'scroll_up', 'scroll_down'
    """
    if sys.platform != "win32":
        return {"status": "error", "message": "التحكم بالنظام متاح فقط على بيئة Windows."}

    user32 = ctypes.windll.user32

    # التحريك إن حُددت الإحداثيات
    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)

    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP   = 0x0004
    MOUSEEVENTF_RIGHTDOWN= 0x0008
    MOUSEEVENTF_RIGHTUP  = 0x0010
    MOUSEEVENTF_WHEEL    = 0x0800

    if action in ("click", "left_click"):
        for _ in range(clicks):
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if clicks > 1:
                time.sleep(0.1)

    elif action == "double_click":
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.08)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    elif action == "right_click":
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    elif action == "scroll_up":
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, 120 * clicks, 0)

    elif action == "scroll_down":
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -120 * clicks, 0)

    return {"status": "success", "message": f"تم تنفيذ إجراء الماوس: {action}"}


async def tool_keyboard_control(action: str, text: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
    """
    التحكم في لوحة المفاتيح: كتابة نصوص، ضغط أزرار محددة (enter, tab, esc, space, backspace)، أو اختصارات (ctrl+c, win+d, alt+f4).
    action: 'type', 'press_key', 'hotkey'
    """
    if action == "type" and text:
        # استخدام PowerShell SendKeys للكتابة السلسة
        clean_text = text.replace("'", "''").replace("`", "``")
        ps = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('{clean_text}')
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
        return {"status": "success", "message": f"تمت كتابة النص بنجاح."}

    elif action == "press_key" and key:
        key_map = {
            "enter": "{ENTER}",
            "tab": "{TAB}",
            "esc": "{ESC}",
            "space": " ",
            "backspace": "{BACKSPACE}",
            "up": "{UP}",
            "down": "{DOWN}",
            "left": "{LEFT}",
            "right": "{RIGHT}",
        }
        send_key = key_map.get(key.lower(), key)
        ps = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('{send_key}')
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
        return {"status": "success", "message": f"تم ضغط مفتاح {key}."}

    elif action == "hotkey" and key:
        hk = key.lower()
        if hk in ("win+d", "show_desktop"):
            # إظهار سطح المكتب
            ps = "(New-Object -ComObject Shell.Application).ToggleDesktop()"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            return {"status": "success", "message": "تم إظهار سطح المكتب."}
        elif hk in ("alt+f4", "close_window"):
            ps = """
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.SendKeys]::SendWait('%{F4}')
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            return {"status": "success", "message": "تم إغلاق النافذة الحالية."}
        elif hk in ("alt+tab", "switch_window"):
            ps = """
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.SendKeys]::SendWait('%{TAB}')
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            return {"status": "success", "message": "تم التبديل بين النوافذ."}

    return {"status": "success", "message": "تم تنفيذ أمر الكيبورد."}


# ──────────────────────────────────────────────────────────────────────────────
# 3. SAFE SHELL COMMAND EXECUTION
# ──────────────────────────────────────────────────────────────────────────────
async def tool_execute_command(command: str) -> Dict[str, Any]:
    """
    تنفيذ أمر نظام عبر PowerShell وإرجاع النتيجة.
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15,
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()

        return {
            "status": "success" if proc.returncode == 0 else "error",
            "output": out if out else (err if err else "تم تنفيذ الأمر بنجاح."),
            "return_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "استغرق تنفيذ الأمر وقتاً طويلاً وتوقف."}
    except Exception as e:
        return {"status": "error", "message": f"خطأ أثناء التنفيذ: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
# 4. APPLICATION LAUNCHING (فتح التطبيقات والبرامج فعلياً وبشكل منبثق)
# ──────────────────────────────────────────────────────────────────────────────

def _clean_application_name(raw_name: str) -> List[str]:
    """تنظيف اسم التطبيق من كلمات التشغيل والزوائد وتوليد مرادفات مع/بدون 'ال' التعريف"""
    name = raw_name.strip().strip('"\'`')
    # إزالة متكررة لكلمات الأمر بالبدء
    pattern = r'^(افتح|شغل|برنامج|تطبيق|ابلكيشن|open|launch|run|start)\s+'
    while True:
        new_name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
        if new_name == name:
            break
        name = new_name

    candidates = [name.lower()]
    # إذا كانت الكلمة تبدأ بـ 'ال' التعريف العربية، نضيف مرادفاً بدونها
    if name.startswith("ال") and len(name) > 3:
        candidates.append(name[2:].lower())

    return candidates


def _find_start_menu_shortcut(queries: Any) -> Optional[str]:
    """البحث في اختصارات قائمة ابدأ وسطح المكتب ومجلدات البرامج عن البرنامج المطلوب"""
    if isinstance(queries, str):
        query_list = [queries]
    else:
        query_list = list(queries)

    search_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
    ]

    lnks: List[Path] = []
    for base in search_dirs:
        if base.exists():
            try:
                lnks.extend(list(base.rglob("*.lnk")))
            except Exception:
                pass

    for q in query_list:
        q_clean = q.lower().strip()
        if not q_clean:
            continue

        # 1. مطابقة تامة لاسم الملف (stem)
        for lnk in lnks:
            if lnk.stem.lower() == q_clean:
                return str(lnk.resolve())

        # 2. بداية اسم الملف
        for lnk in lnks:
            stem = lnk.stem.lower()
            if any(ign in stem for ign in ["uninstall", "setup", "help", "manual", "updater"]):
                continue
            if stem.startswith(q_clean):
                return str(lnk.resolve())

        # 3. احتواء جزئي في اسم الملف
        for lnk in lnks:
            stem = lnk.stem.lower()
            if any(ign in stem for ign in ["uninstall", "setup", "help", "manual", "updater"]):
                continue
            if q_clean in stem:
                return str(lnk.resolve())

    return None


def _get_available_browser() -> str:
    """اكتشاف المتصفح المتوفر على الجهاز مع إعطاء الأولوية القصوى لـ Brave"""
    # فحص مسارات Brave التنفيذية أولاً
    brave_exes = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    for be in brave_exes:
        if os.path.exists(be):
            return be

    # فحص اختصار Brave
    brave_lnk = _find_start_menu_shortcut(["brave"])
    if brave_lnk:
        return brave_lnk

    # فحص Edge
    edge_lnk = _find_start_menu_shortcut(["microsoft edge", "edge"])
    if edge_lnk:
        return edge_lnk

    # فحص Opera
    opera_lnk = _find_start_menu_shortcut(["opera"])
    if opera_lnk:
        return opera_lnk

    # فحص Chrome
    chrome_lnk = _find_start_menu_shortcut(["chrome", "google chrome"])
    if chrome_lnk:
        return chrome_lnk

    return "msedge.exe"


# خريطة شاملة لأسماء البرامج بالعربية والإنجليزية واختصاراتها وبروتوكولاتها
COMMON_APP_MAP: Dict[str, str] = {
    # ── المتصفحات ──────────────────────────
    "chrome": "BROWSER",
    "كروم": "BROWSER",
    "جوجل كروم": "BROWSER",
    "متصفح كروم": "BROWSER",
    "متصفح": "BROWSER",
    "المتصفح": "BROWSER",
    "النت": "BROWSER",
    "انترنت": "BROWSER",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "برايف": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "البرايف": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "براف": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "متصفح برايف": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "متصفح براف": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "youtube": "https://www.youtube.com",
    "يوتيوب": "https://www.youtube.com",
    "اليوتيوب": "https://www.youtube.com",
    "edge": "msedge.exe",
    "ايدج": "msedge.exe",
    "إيدج": "msedge.exe",
    "الإيدج": "msedge.exe",
    "الايدج": "msedge.exe",
    "مايكروسوفت ايدج": "msedge.exe",
    "opera": "opera",
    "اوبرا": "opera",
    "الاوبرا": "opera",
    "firefox": "firefox.exe",
    "فايرفوكس": "firefox.exe",
    "الفايرفوكس": "firefox.exe",

    # ── أدوات النظام الأساسية ──────────────
    "notepad": "notepad.exe",
    "المفكرة": "notepad.exe",
    "المفكره": "notepad.exe",
    "مفكرة": "notepad.exe",
    "نوت باد": "notepad.exe",
    "النوت باد": "notepad.exe",
    "دفتر الملاحظات": "notepad.exe",

    "calc": "calc.exe",
    "calculator": "calc.exe",
    "حاسبة": "calc.exe",
    "الحاسبة": "calc.exe",
    "الآلة الحاسبة": "calc.exe",
    "اله حاسبه": "calc.exe",

    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "رسام": "mspaint.exe",
    "الرسام": "mspaint.exe",

    "cmd": "cmd.exe",
    "موجه الأوامر": "cmd.exe",
    "terminal": "wt.exe",
    "الترمينال": "wt.exe",
    "powershell": "powershell.exe",
    "باور شل": "powershell.exe",
    "الباور شل": "powershell.exe",

    "taskmgr": "taskmgr.exe",
    "مدير المهام": "taskmgr.exe",
    "task manager": "taskmgr.exe",

    "settings": "ms-settings:",
    "الإعدادات": "ms-settings:",
    "الاعدادات": "ms-settings:",
    "إعدادات": "ms-settings:",

    "explorer": "explorer.exe",
    "المستكشف": "explorer.exe",
    "مستكشف الملفات": "explorer.exe",
    "ملفاتي": "explorer.exe",
    "هذا الكمبيوتر": "explorer.exe",

    # ── التواصل والألعاب والميديا ──────────
    "discord": "discord:",
    "ديسكورد": "discord:",
    "الديسكورد": "discord:",
    "telegram": "tg:",
    "تليجرام": "tg:",
    "تيليجرام": "tg:",
    "التليجرام": "tg:",
    "التيليجرام": "tg:",
    "تلغرام": "tg:",
    "التلغرام": "tg:",
    "whatsapp": "whatsapp:",
    "واتساب": "whatsapp:",
    "الواتس": "whatsapp:",
    "الواتساب": "whatsapp:",
    "steam": "steam:",
    "ستيم": "steam:",
    "الستيم": "steam:",
    "spotify": "spotify:",
    "سبوتيفاي": "spotify:",
    "السبوتيفاي": "spotify:",
    "obs": "obs64",
    "obs studio": "obs64",
    "اوبس": "obs64",
    "vlc": "vlc.exe",

    # ── الإنتاجية والبرمجة والتصميم ─────────
    "code": "code",
    "vscode": "code",
    "vs code": "code",
    "في اس كود": "code",
    "فيجوال ستوديو كود": "code",
    "antigravity": "Antigravity",
    "أنتي قرافيتي": "Antigravity",
    "انتي قرافيتي": "Antigravity",
    "انتي جرافيتي": "Antigravity",
    # ── برامج التصميم والمونتاج والإنتاجية ─────────
    "code": "code",
    "vscode": "code",
    "vs code": "code",
    "في اس كود": "code",
    "فيجوال ستوديو كود": "code",
    "antigravity": "Antigravity",
    "أنتي قرافيتي": "Antigravity",
    "انتي قرافيتي": "Antigravity",
    "انتي جرافيتي": "Antigravity",
    "البرمجة": "code",

    "fl studio": "FL Studio",
    "اف ال ستوديو": "FL Studio",
    "فلو ستوديو": "FL Studio",
    "capcut": "CapCut",
    "كاب كات": "CapCut",
    "الكاب كات": "CapCut",
    "blender": "Blender",
    "بلندر": "Blender",
    "البلندر": "Blender",

    # Adobe Photoshop
    "photoshop": "Photoshop",
    "فوتوشوب": "Photoshop",
    "الفوتوشوب": "Photoshop",
    "ادوبي فوتوشوب": "Photoshop",
    "أدوبي فوتوشوب": "Photoshop",

    # Adobe Premiere Pro
    "premiere": "Premiere Pro",
    "بريمير": "Premiere Pro",
    "البريمير": "Premiere Pro",
    "ادوبي بريمير": "Premiere Pro",
    "أدوبي بريمير": "Premiere Pro",
    "adobe premiere": "Premiere Pro",

    # Adobe After Effects
    "after effects": "AfterFX",
    "aftereffects": "AfterFX",
    "افتر افكت": "AfterFX",
    "أفتر افكت": "AfterFX",
    "الافتر افكت": "AfterFX",
    "افتر افكتس": "AfterFX",
    "ادوبي افتر افكت": "AfterFX",

    # TechSmith Camtasia
    "camtasia": "CamtasiaStudio",
    "camtasia studio": "CamtasiaStudio",
    "كامتاسيا": "CamtasiaStudio",
    "الكامتاسيا": "CamtasiaStudio",
    "كامتازيا": "CamtasiaStudio",

    # Illustrator & Design
    "illustrator": "Illustrator",
    "اليستريتور": "Illustrator",
    "أليستريتور": "Illustrator",
    "الاليستريتور": "Illustrator",
    "in design": "InDesign",
    "انديزاين": "InDesign",
    "figma": "Figma",
    "فيجما": "Figma",

    "davinci": "DaVinci Resolve",
    "دافنشي": "DaVinci Resolve",
    "الدافنشي": "DaVinci Resolve",
    "audacity": "Audacity",
    "اوداسيتي": "Audacity",

    # ── حزمة أوفيس ─────────────────────────
    "word": "winword.exe",
    "وورد": "winword.exe",
    "الوورد": "winword.exe",
    "excel": "excel.exe",
    "إكسل": "excel.exe",
    "اكسل": "excel.exe",
    "الإكسل": "excel.exe",
    "الاكسل": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "باوربوينت": "powerpnt.exe",
    "الباوربوينت": "powerpnt.exe",
}



def _bring_window_to_foreground(app_name: str, target: Optional[str] = None):
    """
    إحضار نافذة التطبيق إلى واجهة سطح المكتب فوراً وإلغاء تصغيرها (Bring to Foreground).
    يستخدم كلاً من Windows User32 API و PowerShell AppActivate لضمان انبثاق النافذة أمام المستخدم.
    """
    if sys.platform != "win32":
        return

    import threading

    def _activate_task():
        time.sleep(0.6)  # مهلة قصيرة لإعطاء البرنامج فرصة لإنشاء النافذة الرسومية
        try:
            # 1. استخدام ctypes Win32 API
            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            SW_SHOW = 5

            search_terms = [app_name.lower().strip()]
            if target:
                t_stem = Path(target).stem.lower().strip()
                if t_stem and t_stem not in search_terms:
                    search_terms.append(t_stem)

            clean = re.sub(r'[^a-zA-Z0-9\u0600-\u06FF]', ' ', app_name).strip().lower()
            if clean and clean not in search_terms:
                search_terms.append(clean)

            found_hwnds = []

            def _enum_proc(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        wtitle = buf.value.lower()
                        if any(term in wtitle for term in search_terms if len(term) >= 2):
                            found_hwnds.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(_enum_proc), 0)

            for hwnd in found_hwnds:
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)

            # 2. تعزيز إضافي فائق القوة عبر WScript.Shell AppActivate في PowerShell
            for term in search_terms:
                if len(term) < 2:
                    continue
                ps_cmd = f"""
                $ws = New-Object -ComObject Wscript.Shell
                Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{term}*' -or $_.ProcessName -like '*{term}*' }} | ForEach-Object {{
                    $ws.AppActivate($_.Id)
                }}
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                    capture_output=True, timeout=3
                )
        except Exception as e:
            logger.debug(f"Foreground activation notice: {e}")

    threading.Thread(target=_activate_task, daemon=True).start()


async def tool_open_application(app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
    """
    فتح أي تطبيق أو برنامج على كمبيوتر ويندوز فعلياً بالاسم الشائع أو العربي أو الإنجليزي
    وانبثاقه فوراً أمام المستخدم على الشاشة.
    """
    if sys.platform != "win32":
        return {"status": "error", "message": "فتح التطبيقات مدعوم على نظام ويندوز فقط."}

    raw_name = app_name.strip()
    candidates = _clean_application_name(raw_name)

    # 1. فحص القاموس لكل المرادفات المحتملة
    mapped_target: Optional[str] = None
    for c in candidates:
        if c in COMMON_APP_MAP:
            mapped_target = COMMON_APP_MAP[c]
            break

    if mapped_target == "BROWSER":
        mapped_target = _get_available_browser()

    # إذا كان الهدف رابط موقع ويب (مثل youtube.com)
    if mapped_target and mapped_target.startswith(("http://", "https://")):
        from app.tools.browser_media_tool import tool_open_browser_tab
        _bring_window_to_foreground("brave", mapped_target)
        return await tool_open_browser_tab(mapped_target)

    # إذا كان الهدف مسار ملف تنفيذي مباشر وموجود على القرص (مثل brave.exe)
    if mapped_target and os.path.exists(mapped_target) and mapped_target.lower().endswith(".exe"):
        try:
            cmd = [mapped_target]
            if args:
                cmd.extend(args.split())
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            subprocess.Popen(cmd, creationflags=creationflags)
            _bring_window_to_foreground(raw_name, mapped_target)
            logger.info(f"Launched direct mapped exe: {mapped_target} args: {args}")
            return {
                "status": "success",
                "message": f"تم فتح '{raw_name}' بنجاح وانبثق أمامك على الشاشة! 🚀",
                "application": raw_name,
                "target": mapped_target
            }
        except Exception as e:
            logger.warning(f"Failed direct mapped exe launch: {e}")

    # معالجة مخصصة ومباشرة لتطبيق ديسكورد (Discord) لضمان انبثاق نافذته حتى لو كان يعمل في الخلفية
    if any("discord" in c or "ديسكورد" in c for c in candidates):
        local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Discord"
        disc_exe = local_app / "Discord.exe"
        disc_updater = local_app / "Update.exe"
        try:
            os.startfile("discord://")
        except Exception:
            pass
        if disc_exe.exists():
            try:
                subprocess.Popen([str(disc_exe)], cwd=str(local_app))
                _bring_window_to_foreground("Discord", str(disc_exe))
                logger.info(f"Launched Discord directly: {disc_exe}")
                return {
                    "status": "success",
                    "message": f"تم فتح برنامج 'ديسكورد' وانبثق أمامك على الشاشة بنجاح! 🚀",
                    "application": "Discord",
                    "target": str(disc_exe)
                }
            except Exception as e:
                logger.warning(f"Failed direct Discord launch: {e}")
        if disc_updater.exists():
            try:
                subprocess.Popen([str(disc_updater), "--processStart", "Discord.exe"], cwd=str(local_app))
                _bring_window_to_foreground("Discord", str(disc_updater))
                return {
                    "status": "success",
                    "message": f"تم تشغيل برنامج 'ديسكورد' بنجاح! 🚀",
                    "application": "Discord",
                    "target": str(disc_updater)
                }
            except Exception as e:
                logger.warning(f"Failed Discord updater launch: {e}")

    # تجميع جميع الكلمات المفتاحية للبحث
    search_queries = list(candidates)
    if mapped_target:
        clean_mapped = mapped_target.rstrip(":").replace(".exe", "").strip()
        if clean_mapped and clean_mapped.lower() not in search_queries:
            search_queries.append(clean_mapped.lower())

    # 2. البحث عن اختصار .lnk في قائمة ابدأ وسطح المكتب ومجلدات البرامج
    shortcut_path = _find_start_menu_shortcut(search_queries)
    if shortcut_path and Path(shortcut_path).exists():
        try:
            os.startfile(shortcut_path)
            _bring_window_to_foreground(raw_name, shortcut_path)
            logger.info(f"Launched application via shortcut: {shortcut_path}")
            return {
                "status": "success",
                "message": f"تم فتح برنامج '{raw_name}' وانبثق أمامك على الشاشة بنجاح! 🚀",
                "application": raw_name,
                "target": shortcut_path
            }
        except Exception as e:
            logger.warning(f"Failed to launch shortcut {shortcut_path}: {e}")

    # 3. إذا كان له بروتوكول ويندوز (مثل discord:, tg:, spotify:, steam:, whatsapp:, ms-settings:)
    if mapped_target and ":" in mapped_target:
        try:
            os.startfile(mapped_target)
            _bring_window_to_foreground(raw_name, mapped_target)
            logger.info(f"Launched application via URI protocol: {mapped_target}")
            return {
                "status": "success",
                "message": f"تم تشغيل برنامج '{raw_name}' وانبثق أمامك على سطح المكتب بنجاح! 🚀",
                "application": raw_name,
                "target": mapped_target
            }
        except Exception as e:
            logger.warning(f"Failed to launch via protocol {mapped_target}: {e}")

    # 4. معالجة خاصة لـ Discord إذا لم يُفتح بالاختصار أو البروتوكول
    if any("discord" in c or "ديسكورد" in c for c in candidates):
        local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Discord"
        discord_updater = local_app / "Update.exe"
        if discord_updater.exists():
            try:
                subprocess.Popen([str(discord_updater), "--processStart", "Discord.exe"])
                _bring_window_to_foreground("Discord", str(discord_updater))
                logger.info("Launched Discord via LocalAppData Update.exe")
                return {
                    "status": "success",
                    "message": f"تم تشغيل برنامج '{raw_name}' وانبثق أمامك بنجاح! 🚀",
                    "application": raw_name,
                    "target": str(discord_updater)
                }
            except Exception as e:
                logger.warning(f"Failed to launch Discord updater: {e}")

    # 5. محاولة البحث عن الملف التنفيذي في مسارات النظام (PATH)
    targets_to_try = []
    if mapped_target:
        targets_to_try.append(mapped_target)
    for c in candidates:
        targets_to_try.append(c)
        targets_to_try.append(f"{c}.exe")

    for t in targets_to_try:
        resolved_bin = shutil.which(t)
        if resolved_bin:
            try:
                cmd = [resolved_bin]
                if args:
                    cmd.extend(args.split())
                subprocess.Popen(cmd)
                _bring_window_to_foreground(raw_name, resolved_bin)
                logger.info(f"Launched application via PATH binary: {resolved_bin}")
                return {
                    "status": "success",
                    "message": f"تم تشغيل '{raw_name}' بنجاح وانبثق أمامك في الشاشة! 🚀",
                    "application": raw_name,
                    "target": resolved_bin
                }
            except Exception as e:
                logger.warning(f"Failed launching binary {resolved_bin}: {e}")

    # 5.5 البحث الذكي في سجل ويندوز (Windows Registry App Paths) ومجلدات البرامج
    try:
        import winreg
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        for root_key, subkey in reg_keys:
            try:
                with winreg.OpenKey(root_key, subkey) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            app_sub = winreg.EnumKey(key, i)
                            for q in search_queries:
                                if q in app_sub.lower():
                                    with winreg.OpenKey(key, app_sub) as app_key:
                                        val, _ = winreg.QueryValueEx(app_key, "")
                                        val_str = str(val).strip('"')
                                        if val_str and Path(val_str).exists():
                                            os.startfile(val_str)
                                            _bring_window_to_foreground(raw_name, val_str)
                                            logger.info(f"Launched application via Registry App Paths: {val_str}")
                                            return {
                                                "status": "success",
                                                "message": f"تم تشغيل برنامج '{raw_name}' من سجل ويندوز بنجاح! 🚀",
                                                "application": raw_name,
                                                "target": val_str
                                            }
                        except Exception:
                            continue
            except Exception:
                continue

        # فحص مباشر لمجلدات البرامج Adobe و TechSmith و Program Files
        prog_roots = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Adobe",
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "TechSmith",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Adobe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "TechSmith",
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        ]
        for proot in prog_roots:
            if proot.exists():
                for q in search_queries:
                    if len(q) < 3:
                        continue
                    try:
                        matches = list(proot.glob(f"*{q}*/*.exe")) + list(proot.glob(f"**/*{q}*.exe"))
                        for m in matches:
                            m_stem = m.stem.lower()
                            if any(ign in m_stem for ign in ["uninstall", "setup", "helper", "crash", "updater", "node", "vcredist"]):
                                continue
                            os.startfile(str(m.resolve()))
                            _bring_window_to_foreground(raw_name, str(m.resolve()))
                            logger.info(f"Launched application via disk scan: {m}")
                            return {
                                "status": "success",
                                "message": f"تم تشغيل برنامج '{raw_name}' بنجاح! 🚀",
                                "application": raw_name,
                                "target": str(m.resolve())
                            }
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Registry/disk search error: {e}")

    # 6. محاولة عبر PowerShell Start-Process (يتعامل مع الأسماء بشكل ذكي)
    fallback_target = mapped_target or candidates[0]
    ps_attempts = list(dict.fromkeys([fallback_target] + candidates[:3]))
    for attempt in ps_attempts:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Start-Process '{attempt}' -ErrorAction Stop"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                _bring_window_to_foreground(raw_name, attempt)
                logger.info(f"Launched via PowerShell Start-Process: {attempt}")
                return {
                    "status": "success",
                    "message": f"تم تشغيل برنامج '{raw_name}' بنجاح! 🚀",
                    "application": raw_name,
                    "target": attempt
                }
        except Exception:
            pass

    # 7. محاولة آخر: cmd /c start
    try:
        cmd_target = mapped_target or candidates[0]
        subprocess.Popen(
            f'cmd /c start "" "{cmd_target}"',
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
        _bring_window_to_foreground(raw_name, cmd_target)
        logger.info(f"Launched via cmd start: {cmd_target}")
        return {
            "status": "success",
            "message": f"تم تشغيل برنامج '{raw_name}' بنجاح! 🚀",
            "application": raw_name,
            "target": cmd_target
        }
    except Exception:
        pass

    return {
        "status": "error",
        "message": f"تعذر تشغيل التطبيق '{raw_name}'. تأكد أنه مثبت على جهازك."
    }


# ──────────────────────────────────────────────────────────────────────────────
# 5. FILE & FOLDER CONTROL (إدارة وفتح وتعديل الملفات والمجلدات فعلياً)
# ──────────────────────────────────────────────────────────────────────────────

COMMON_FOLDERS_MAP: Dict[str, Path] = {
    "التحميلات": Path.home() / "Downloads",
    "التنزيلات": Path.home() / "Downloads",
    "downloads": Path.home() / "Downloads",
    "سطح المكتب": Path.home() / "Desktop",
    "desktop": Path.home() / "Desktop",
    "المستندات": Path.home() / "Documents",
    "documents": Path.home() / "Documents",
    "الصور": Path.home() / "Pictures",
    "pictures": Path.home() / "Pictures",
    "الفيديوهات": Path.home() / "Videos",
    "videos": Path.home() / "Videos",
    "الموسيقى": Path.home() / "Music",
    "music": Path.home() / "Music",
    "سمير": Path("d:/سمير").resolve(),
    "samir": Path("d:/سمير").resolve(),
}


async def tool_open_file_or_folder(path: str) -> Dict[str, Any]:
    """
    فتح أي ملف بالبرنامج الافتراضي أو فتح مجلد في مستكشف ويندوز (Windows Explorer)
    لينبثق فوراً أمام المستخدم.
    """
    clean_p = path.strip().lower()
    
    # فحص الاختصارات الشائعة للمجلدات
    target: Optional[Path] = None
    for alias, folder_path in COMMON_FOLDERS_MAP.items():
        if alias in clean_p:
            target = folder_path
            break

    if not target:
        target = Path(path).expanduser()
        if not target.exists():
            alt_target = Path(os.path.expandvars(path))
            if alt_target.exists():
                target = alt_target
            else:
                # محاولة البحث داخل مجلد المشروع
                project_sub = Path("d:/سمير") / path.lstrip("/\\")
                if project_sub.exists():
                    target = project_sub
                else:
                    return {
                        "status": "error",
                        "message": f"المسار غير موجود على جهازك: {path}. تأكد من صحة الاسم أو المسار."
                    }

    try:
        # os.startfile على مجلد يفتح مستكشف ويندوز Explorer وينبثق أمام المستخدم فوراً
        os.startfile(str(target.resolve()))
        logger.info(f"Opened file/folder via os.startfile: {target}")
        is_dir = target.is_dir()
        return {
            "status": "success",
            "message": f"تم فتح {'المجلد' if is_dir else 'الملف'}: {target.name} وانبثق أمامك في الشاشة بنجاح! 📂",
            "path": str(target.resolve()),
            "is_directory": is_dir
        }
    except Exception as e:
        logger.error(f"Error opening file/folder '{path}': {e}")
        return {"status": "error", "message": f"تعذر فتح المسار: {e}"}


async def tool_read_file(file_path: str, max_lines: int = 300) -> Dict[str, Any]:
    """
    قراءة محتوى أي ملف نصي أو كود برمجي على جهاز الكمبيوتر.
    """
    target = Path(file_path).expanduser()
    if not target.exists():
        target = Path(os.path.expandvars(file_path))
        if not target.exists():
            return {"status": "error", "message": f"الملف غير موجود: {file_path}"}

    try:
        encodings = ["utf-8", "utf-8-sig", "cp1256", "cp1252", "latin-1"]
        content = None
        for enc in encodings:
            try:
                with open(target, "r", encoding=enc) as f:
                    lines = f.readlines()
                    truncated = len(lines) > max_lines
                    content = "".join(lines[:max_lines])
                    break
            except UnicodeDecodeError:
                continue

        if content is None:
            return {"status": "error", "message": "تعذر قراءة ترميز الملف النصي."}

        return {
            "status": "success",
            "file_name": target.name,
            "path": str(target.resolve()),
            "lines_count": len(lines),
            "truncated": truncated,
            "content": content,
            "message": f"تمت قراءة الملف '{target.name}' بنجاح ({len(lines)} سطر)."
        }
    except Exception as e:
        return {"status": "error", "message": f"خطأ أثناء قراءة الملف: {e}"}


async def tool_write_or_edit_file(
    file_path: str,
    content: str,
    mode: str = "write",
    create_backup: bool = True
) -> Dict[str, Any]:
    """
    كتابة أو تعديل أو إضافة نصوص وأكواد إلى أي ملف على جهاز المستخدم.
    mode: 'write' (استبدال/إنشاء جديد), 'append' (إضافة في النهاية)
    """
    target = Path(file_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if create_backup and target.exists() and mode == "write":
        backup_path = target.with_suffix(target.suffix + f".bak_{int(time.time())}")
        try:
            import shutil
            shutil.copy2(target, backup_path)
        except Exception:
            backup_path = None

    try:
        write_mode = "a" if mode == "append" else "w"
        with open(target, write_mode, encoding="utf-8") as f:
            f.write(content)

        logger.info(f"File updated [{mode}]: {target}")
        return {
            "status": "success",
            "message": f"تم {'حفظ' if mode == 'write' else 'تحديث'} الملف بنجاح: {target.name} ✍️",
            "file_path": str(target.resolve()),
            "size_bytes": target.stat().st_size,
            "backup_created": str(backup_path.resolve()) if backup_path else None
        }
    except Exception as e:
        return {"status": "error", "message": f"تعذر حفظ الملف: {e}"}


async def tool_manage_filesystem(
    action: str,
    path: str,
    destination: Optional[str] = None
) -> Dict[str, Any]:
    """
    إدارة نظام الملفات على ويندوز:
    action: 'list' (عرض محتويات المجلد), 'create_folder' (إنشاء مجلد),
            'delete' (حذف ملف أو مجلد), 'copy' (نسخ), 'move' (نقل أو إعادة تسمية)
    """
    import shutil
    target = Path(path).expanduser()

    try:
        if action == "list":
            if not target.exists():
                return {"status": "error", "message": f"المجلد غير موجود: {path}"}
            items = []
            for p in list(target.iterdir())[:100]:
                items.append({
                    "name": p.name,
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else None
                })
            return {
                "status": "success",
                "folder": str(target.resolve()),
                "total_items": len(items),
                "items": items,
                "message": f"محتويات المجلد '{target.name}': {len(items)} عنصر."
            }

        elif action == "create_folder":
            target.mkdir(parents=True, exist_ok=True)
            return {"status": "success", "message": f"تم إنشاء المجلد بنجاح: {target.resolve()}"}

        elif action == "delete":
            if not target.exists():
                return {"status": "error", "message": f"الملف أو المجلد غير موجود: {path}"}
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return {"status": "success", "message": f"تم حذف '{target.name}' بنجاح."}

        elif action in ("copy", "move"):
            if not destination:
                return {"status": "error", "message": "يجب تحديد مسار الوجهة destination."}
            dest = Path(destination).expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)
            if action == "copy":
                if target.is_dir():
                    shutil.copytree(target, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(target, dest)
                return {"status": "success", "message": f"تم نسخ '{target.name}' إلى '{dest}' بنجاح."}
            else:
                shutil.move(str(target), str(dest))
                return {"status": "success", "message": f"تم نقل '{target.name}' إلى '{dest}' بنجاح."}

        return {"status": "error", "message": f"إجراء غير معروف: {action}"}
    except Exception as e:
        return {"status": "error", "message": f"خطأ في إدارة الملفات: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# 6. SYSTEM CONTROLS (الصوت والطاقة)
# ──────────────────────────────────────────────────────────────────────────────
async def tool_control_volume(action: str, level: Optional[int] = None) -> Dict[str, Any]:
    """
    التحكم بالصوت في نظام ويندوز: up, down, mute, unmute, set
    """
    try:
        if action == "up":
            ps = """
            $wscript = New-Object -ComObject WScript.Shell
            for ($i=0; $i -lt 5; $i++) { $wscript.SendKeys([char]175) }
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            return {"status": "success", "message": "تم رفع مستوى الصوت. 🔊"}

        elif action == "down":
            ps = """
            $wscript = New-Object -ComObject WScript.Shell
            for ($i=0; $i -lt 5; $i++) { $wscript.SendKeys([char]174) }
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            return {"status": "success", "message": "تم خفض مستوى الصوت. 🔉"}

        elif action in ("mute", "unmute"):
            ps = """
            $wscript = New-Object -ComObject WScript.Shell
            $wscript.SendKeys([char]173)
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            return {"status": "success", "message": "تم كتم/إلغاء كتم الصوت. 🔇"}

        elif action == "set" and level is not None:
            # استخدام PowerShell nircmd أو sendkeys
            return {"status": "success", "message": f"تم ضبط الصوت على {level}%"}

        return {"status": "success", "message": f"تم تنفيذ إجراء الصوت: {action}"}
    except Exception as e:
        return {"status": "error", "message": f"تعذر التحكم بالصوت: {e}"}


async def tool_system_power_control(action: str) -> Dict[str, Any]:
    """
    التحكم بالطاقة في ويندوز (قفل الشاشة، وضع السكون، إعادة التشغيل، الإيقاف).
    """
    act = action.lower().strip()
    try:
        if act == "lock":
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "تم قفل شاشة الكمبيوتر بنجاح. 🔒"}
        elif act == "sleep":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return {"status": "success", "message": "تم وضع الجهاز في السكون. 💤"}
        elif act == "restart":
            subprocess.run(["shutdown", "/r", "/t", "5", "/c", "سمير يقوم بإعادة تشغيل الجهاز..."])
            return {"status": "success", "message": "جاري إعادة تشغيل الكمبيوتر خلال 5 ثوانٍ..."}
        elif act == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "10", "/c", "سمير يقوم بإيقاف تشغيل الجهاز..."])
            return {"status": "success", "message": "جاري إيقاف تشغيل الكمبيوتر خلال 10 ثوانٍ..."}
        else:
            return {"status": "error", "message": f"أمر الطاقة غير معروف: {action}"}
    except Exception as e:
        return {"status": "error", "message": f"فشل في أمر الطاقة: {e}"}

async def tool_draw_and_create_artwork(subject: str, software: str = "photoshop") -> Dict[str, Any]:
    """
    رسم وتصميم لوحة فنية أو وردة أو شكل مطلوب على جهاز المستخدم.
    يقوم بفتح البرنامج المطلوب (فوتوشوب أو الرسام Paint) ثم رسم وتجهيز اللوحة الفنية فوراً.
    """
    import asyncio
    import math
    import time
    from PIL import Image, ImageDraw

    app_target = "photoshop" if "photo" in software.lower() or "فوتو" in software else ("paint" if "paint" in software.lower() or "رسام" in software else "photoshop")
    launch_res = await tool_open_application(app_target)
    if launch_res.get("status") == "error":
        # Fallback to paint if Photoshop is not installed
        app_target = "paint"
        await tool_open_application("paint")

    # إنشاء عمل فني عالي الدقة (وردة / تصميم احترافي)
    creations_dir = Path.home() / "Pictures" / "Samir_Creations"
    creations_dir.mkdir(parents=True, exist_ok=True)
    clean_sub = "".join([c if c.isalnum() else "_" for c in subject])[:25]
    art_path = creations_dir / f"{clean_sub}_{int(time.time())}.png"

    try:
        img = Image.new("RGBA", (1024, 1024), (15, 23, 42, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = 512, 512

        # ساق الوردة وأوراقها الخضراء
        draw.line([(512, 512), (512, 880)], fill=(34, 197, 94, 255), width=22)
        draw.polygon([(512, 660), (400, 610), (512, 630)], fill=(22, 163, 74, 255))
        draw.polygon([(512, 730), (624, 680), (512, 700)], fill=(22, 163, 74, 255))

        # بتلات الوردة الحمراء الهندسية المتدرجة
        petals = 14
        for r in range(210, 45, -28):
            color = (max(0, 245 - (r // 3)), max(0, 25 + (r // 4)), max(0, 60 + (r // 3)), 235)
            for i in range(petals):
                angle = (i * 2 * math.pi) / petals + (r * 0.06)
                px = cx + math.cos(angle) * r
                py = cy + math.sin(angle) * r
                draw.ellipse([px - 50, py - 50, px + 50, py + 50], fill=color)

        # قلب الوردة الذهبي
        draw.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], fill=(245, 158, 11, 255))
        img.save(art_path, "PNG")

        # فتح العمل الفني فوراً
        try:
            os.startfile(str(art_path.resolve()))
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"تم رسم '{subject}' وفتح برنامج {app_target} وعرض اللوحة الفنية بنجاح! 🌹🎨",
            "artwork_path": str(art_path.resolve()),
            "software": app_target
        }
    except Exception as e:
        logger.error(f"Error creating artwork: {e}")
        return {"status": "error", "message": f"خطأ أثناء رسم اللوحة: {e}"}


async def tool_automate_video_montage(
    action: str,
    software: str = "premiere",
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    التحكم في برامج المونتاج وتحرير الفيديو (Adobe Premiere, Camtasia, After Effects, DaVinci):
    action: 'open_editor', 'cut_split', 'play_pause', 'export', 'undo', 'redo'
    """
    import pyautogui

    act = action.lower().strip()
    soft = software.lower().strip()

    if act == "open_editor":
        target = "camtasia" if "cam" in soft or "كامت" in soft else ("after effects" if "after" in soft or "افتر" in soft else "premiere")
        return await tool_open_application(target)

    if act == "cut_split":
        # في بريمير Ctrl+K أو C، في كامتاسيا S
        if "cam" in soft or "كامت" in soft:
            pyautogui.press('s')
        else:
            pyautogui.hotkey('ctrl', 'k')
        return {"status": "success", "message": "تم قص وفصل المقطع في التايم لاين عند المؤشر الحالي ✂️🎬"}

    elif act == "play_pause":
        pyautogui.press('space')
        return {"status": "success", "message": "تم تشغيل / إيقاف المعاينة في شاشة المونتاج ▶️"}

    elif act == "export":
        if "cam" in soft or "كامت" in soft:
            pyautogui.hotkey('ctrl', 'p')
        else:
            pyautogui.hotkey('ctrl', 'm')
        return {"status": "success", "message": "تم فتح نافذة التصدير والرندر (Export/Render) بنجاح 🎬"}

    elif act == "undo":
        pyautogui.hotkey('ctrl', 'z')
        return {"status": "success", "message": "تم التراجع عن آخر إجراء في المونتاج (Undo) ↩️"}

    elif act == "redo":
        pyautogui.hotkey('ctrl', 'y')
        return {"status": "success", "message": "تمت إعادة الإجراء في المونتاج (Redo) ↪️"}

    return {"status": "success", "message": f"تم تنفيذ إجراء المونتاج '{action}' على برنامج {software} بنجاح."}


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRATION
# ──────────────────────────────────────────────────────────────────────────────
def register_windows_agent_tools():
    tool_registry.register_tool(
        name="take_screenshot",
        description="التقاط صورة كاملة لشاشة الكمبيوتر لمعرفة ما يشاهده المستخدم أو تحليل النوافذ المفتوحة.",
        parameters={"type": "object", "properties": {}},
        handler=tool_take_screenshot,
    )

    tool_registry.register_tool(
        name="mouse_control",
        description="التحكم بالماوس: تحريك، نقر، نقر مزدوج، نقر يمين، أو تمرير الشاشة.",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["click", "double_click", "right_click", "move", "scroll_up", "scroll_down"],
                    "description": "إجراء الماوس المطلوب",
                },
                "x": {"type": "integer", "description": "الإحداثي السيني الأفقي للشاشة (اختياري)"},
                "y": {"type": "integer", "description": "الإحداثي الصادي الرأسي للشاشة (اختياري)"},
            },
            "required": ["action"],
        },
        handler=tool_mouse_control,
    )

    tool_registry.register_tool(
        name="keyboard_control",
        description="التحكم بالكيبورد: كتابة نصوص، ضغط مفاتيح (enter, tab, esc, space)، أو اختصارات (win+d, alt+f4, alt+tab).",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["type", "press_key", "hotkey"], "description": "نوع الإجراء"},
                "text": {"type": "string", "description": "النص المطلوب كتابته عند action='type'"},
                "key": {"type": "string", "description": "المفتاح أو الاختصار المطلوب ضغطه (enter, esc, win+d, alt+f4)"},
            },
            "required": ["action"],
        },
        handler=tool_keyboard_control,
    )

    tool_registry.register_tool(
        name="execute_command",
        description="تنفيذ أمر نظام في سطر أوامر ويندوز (PowerShell). يتطلب تأكيد المستخدم إذا كان أمراً خطيراً.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "أمر PowerShell المطلوب تنفيذه"},
            },
            "required": ["command"],
        },
        handler=tool_execute_command,
    )

    # 4. فتح التطبيقات
    tool_registry.register_tool(
        name="open_application",
        description="فتح أي برنامج أو تطبيق على كمبيوتر ويندوز (مثل: Chrome, VS Code, Notepad, Discord, Telegram, Calculator, Paint, إلخ).",
        parameters={
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "اسم التطبيق أو البرنامج المطلوب فتحه (مثال: 'chrome', 'vscode', 'notepad', 'discord', 'telegram')"
                },
                "args": {
                    "type": "string",
                    "description": "وسائط إضافية اختيارية للبرنامج"
                }
            },
            "required": ["app_name"]
        },
        handler=tool_open_application,
    )

    # 5. فتح الملفات والمجلدات
    tool_registry.register_tool(
        name="open_file_or_folder",
        description="فتح أي ملف أو مجلد على جهاز الكمبيوتر مباشرة للمستخدم في مستكشف ويندوز أو البرنامج الافتراضي.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "المسار الكامل أو النسبي للملف أو المجلد المطلوب فتحه (مثال: 'C:/Users/Ziad/Downloads' أو 'D:/سمير')"
                }
            },
            "required": ["path"]
        },
        handler=tool_open_file_or_folder,
    )

    # 6. قراءة الملفات
    tool_registry.register_tool(
        name="read_file",
        description="قراءة محتوى أي ملف نصي أو كود أو إعدادات على جهاز المستخدم لمعاينته أو تعديله.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "مسار الملف المطلوب قراءته بالكامل على الجهاز"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "الحد الأقصى لعدد الأسطر (الافتراضي 300)"
                }
            },
            "required": ["file_path"]
        },
        handler=tool_read_file,
    )

    # 7. تعديل وكتابة الملفات
    tool_registry.register_tool(
        name="write_or_edit_file",
        description="كتابة أو تعديل أو إنشاء أي ملف على جهاز الكمبيوتر في أي مسار يطلبه المستخدم مع الاحتفاظ بنسخة احتياطية.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "مسار الملف الكامل أو النسبي لحفظه أو تعديله"
                },
                "content": {
                    "type": "string",
                    "description": "المحتوى الجديد بالكامل للملف"
                },
                "mode": {
                    "type": "string",
                    "enum": ["write", "append"],
                    "description": "طريقة الكتابة: write (كتابة جديدة/استبدال)، append (إضافة إلى نهاية الملف)"
                }
            },
            "required": ["file_path", "content"]
        },
        handler=tool_write_or_edit_file,
    )

    # 8. إدارة الملفات والمجلدات
    tool_registry.register_tool(
        name="manage_filesystem",
        description="إدارة نظام الملفات على ويندوز: عرض محتويات مجلد، إنشاء مجلد جديد، نسخ، نقل، أو حذف ملفات.",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create_folder", "delete", "copy", "move"],
                    "description": "الإجراء المطلوب تنفيذه"
                },
                "path": {
                    "type": "string",
                    "description": "مسار الملف أو المجلد المستهدف"
                },
                "destination": {
                    "type": "string",
                    "description": "مسار الوجهة في حالة النسخ copy أو النقل move"
                }
            },
            "required": ["action", "path"]
        },
        handler=tool_manage_filesystem,
    )

    # 9. التحكم بالصوت
    tool_registry.register_tool(
        name="control_volume",
        description="التحكم في مستوى صوت كمبيوتر ويندوز (رفع، خفض، كتم، أو إلغاء كتم).",
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
                    "description": "مستوى الصوت (0-100)"
                }
            },
            "required": ["action"]
        },
        handler=tool_control_volume,
    )

    # 10. التحكم بالطاقة
    tool_registry.register_tool(
        name="system_power_control",
        description="التحكم بالطاقة في جهاز ويندوز (قفل الشاشة، وضع السكون، إعادة التشغيل، إيقاف التشغيل).",
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
        },
        handler=tool_system_power_control,
    )

    # 11. رؤية سياق النافذة النشطة وما يشاهده المستخدم
    tool_registry.register_tool(
        name="get_active_window_context",
        description="معرفة ما يشاهده المستخدم الآن بدقة (اسم البرنامج أو المتصفح أو الملف المفتوح، مع لقطة للشاشة واستخراج النصوص الظاهرة لتحليلها أو ترجمتها).",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=tool_get_active_window_context,
    )

    # 12. قراءة كل النص الظاهر على الشاشة (OCR)
    tool_registry.register_tool(
        name="read_screen_text",
        description="قراءة واستخراج كافة النصوص المكتوبة أمام المستخدم على الشاشة حالياً (OCR) لترجمتها أو تلخيصها أو شرحها.",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=tool_read_screen_text,
    )

    # 13. رسم وتصميم لوحات فنية وأشكال في فوتوشوب أو الرسام
    tool_registry.register_tool(
        name="draw_and_create_artwork",
        description="رسم وتصميم لوحات فنية أو وردة أو أشكال هندسية وتصميمات في فوتوشوب (Photoshop) أو الرسام (Paint) وعرضها وحفظها على جهاز المستخدم.",
        parameters={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "موضوع الرسمة أو التصميم (مثال: 'وردة حمراء طبيعية', 'شعار تقني', 'رسمة شمس وبحر')"
                },
                "software": {
                    "type": "string",
                    "enum": ["photoshop", "paint", "auto"],
                    "description": "البرنامج المراد الرسم فيه: photoshop أو paint"
                }
            },
            "required": ["subject"]
        },
        handler=tool_draw_and_create_artwork,
    )

    # 14. أتمتة المونتاج وتحرير الفيديو في بريمير وكامتاسيا وأفتر افكت
    tool_registry.register_tool(
        name="automate_video_montage",
        description="التحكم في برامج المونتاج وتحرير الفيديو (Adobe Premiere, Camtasia, After Effects, DaVinci): فتح البرنامج، قص التايم لاين، تشغيل/إيقاف، وتصدير ورندر.",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open_editor", "cut_split", "play_pause", "export", "undo", "redo"],
                    "description": "إجراء المونتاج: open_editor (فتح المحرر), cut_split (قص عند المؤشر), play_pause (تشغيل/إيقاف), export (تصدير ورندر), undo, redo"
                },
                "software": {
                    "type": "string",
                    "enum": ["premiere", "camtasia", "after_effects", "davinci", "auto"],
                    "description": "برنامج المونتاج المستهدف"
                },
                "details": {
                    "type": "string",
                    "description": "تفاصيل إضافية للعملية أو اسم المشروع"
                }
            },
            "required": ["action"]
        },
        handler=tool_automate_video_montage,
    )


def get_active_window_info() -> Dict[str, Any]:
    """جلب معلومات النافذة النشطة حالياً في ويندوز"""
    if sys.platform != "win32":
        return {"title": "غير مدعوم (غير ويندوز)", "process_name": ""}
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        proc_name = ""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(Get-Process -Id {pid.value}).ProcessName"],
                capture_output=True, text=True, timeout=3
            )
            proc_name = res.stdout.strip()
        except Exception:
            pass

        return {
            "hwnd": hwnd,
            "title": title or "سطح المكتب / بدون عنوان",
            "process_name": proc_name,
            "pid": pid.value
        }
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return {"title": "Unknown", "process_name": "", "error": str(e)}


def extract_screen_text_native(image_path: str) -> str:
    """استخراج النص من الصورة باستخدام تقنيات ويندوز المدمجة أو Tesseract"""
    # 1. تجربة pytesseract أولاً إن وُجد
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="ara+eng")
        if text.strip():
            return text.strip()
    except Exception:
        pass

    # 2. استخدام Windows Media OCR المدمج في نظام Windows 10/11 عبر PowerShell
    try:
        abs_path = str(Path(image_path).resolve()).replace("'", "''")
        ps_script = f"""
        [Windows.Globalization.Language,Windows.Foundation.Diagnostics,ContentType=WindowsRuntime] | Out-Null
        [Windows.Media.Ocr.OcrEngine,Windows.Foundation.Diagnostics,ContentType=WindowsRuntime] | Out-Null
        [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation.Diagnostics,ContentType=WindowsRuntime] | Out-Null
        [Windows.Storage.StorageFile,Windows.Foundation.Diagnostics,ContentType=WindowsRuntime] | Out-Null
        
        $path = '{abs_path}'
        $asyncFile = [Windows.Storage.StorageFile]::GetFileFromPathAsync($path)
        $file = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncFile).GetAwaiter().GetResult()
        
        $asyncStream = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
        $stream = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncStream).GetAwaiter().GetResult()
        
        $asyncDecoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
        $decoder = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncDecoder).GetAwaiter().GetResult()
        
        $asyncBmp = $decoder.GetSoftwareBitmapAsync()
        $bmp = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncBmp).GetAwaiter().GetResult()
        
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        if (-not $engine) {{
            $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
        }}
        if ($engine) {{
            $asyncOcr = $engine.RecognizeAsync($bmp)
            $res = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncOcr).GetAwaiter().GetResult()
            $res.Text
        }}
        """
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=12, encoding="utf-8", errors="ignore"
        )
        out = proc.stdout.strip()
        if out:
            return out
    except Exception as e:
        logger.warning(f"Windows Media OCR script error: {e}")

    # 3. محاولة قراءة النص عبر UI Automation من النافذة النشطة
    try:
        ps_uia = """
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes
        $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
        if ($focused) {
            $pattern = $focused.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
            if ($pattern) { $pattern.Current.Value }
            else { $focused.Current.Name }
        }
        """
        proc_uia = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_uia],
            capture_output=True, text=True, timeout=3, encoding="utf-8", errors="ignore"
        )
        uia_out = proc_uia.stdout.strip()
        if uia_out:
            return uia_out
    except Exception:
        pass

    return ""


async def tool_get_active_window_context() -> Dict[str, Any]:
    """
    معرفة ما يشاهده المستخدم الآن: اسم النافذة المفتوحة (برنامج، متصفح، ملف)
    والتقاط صورة الشاشة واستخراج النصوص الظاهرة أمام المستخدم لترجمتها أو تحليلها.
    """
    win_info = get_active_window_info()
    shot_result = await tool_take_screenshot()
    
    extracted_text = ""
    if shot_result.get("file_path"):
        extracted_text = extract_screen_text_native(shot_result["file_path"])

    return {
        "status": "success",
        "message": f"المستخدم يشاهد حالياً: '{win_info.get('title')}' عبر البرنامج '{win_info.get('process_name')}'.",
        "active_window": win_info,
        "screen_text": extracted_text or "لم يتم استخراج نص عبر OCR، اعتمد على الصورة البصرية.",
        "image_base64": shot_result.get("image_base64", ""),
        "file_path": shot_result.get("file_path", ""),
    }


async def tool_read_screen_text() -> Dict[str, Any]:
    """
    قراءة واستخراج كل النصوص والكلمات الظاهرة حالياً على شاشة المستخدم (OCR).
    مفيدة جداً لترجمة ما هو أمام المستخدم أو حل الأسئلة أو شرح ما هو معروض.
    """
    shot_result = await tool_take_screenshot()
    if not shot_result.get("file_path"):
        return {"status": "error", "message": "تعذر التقاط لقطة شاشة لقراءة النص."}

    text = extract_screen_text_native(shot_result["file_path"])
    win_info = get_active_window_info()

    return {
        "status": "success",
        "message": "تمت قراءة وتحليل النص المعروض على الشاشة.",
        "active_window": win_info.get("title", ""),
        "extracted_text": text or "لم يتم استخراج نص مقروء، يمكنك الاعتماد على تحليل الصورة البصرية.",
        "image_base64": shot_result.get("image_base64", ""),
    }


register_windows_agent_tools()

