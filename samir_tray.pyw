import os
import sys
import time
import subprocess
import urllib.request
import webbrowser
import threading
from pathlib import Path

# إعداد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(BASE_DIR, "core_server")
VENV_PYTHONW = os.path.join(CORE_DIR, ".venv", "Scripts", "pythonw.exe")
VENV_PYTHON = os.path.join(CORE_DIR, ".venv", "Scripts", "python.exe")
RUN_SERVER = os.path.join(CORE_DIR, "run_server.py")
ICON_PATH = os.path.join(BASE_DIR, "samir.ico")
PORT = 8000
HEALTH_URL = f"http://localhost:{PORT}/health"
APP_URL = f"http://localhost:{PORT}/"

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# متغيرات حالة الخادم
server_status = "starting"  # "online", "offline", "starting"
last_check_time = 0
tray_icon_instance = None


def is_server_ready() -> bool:
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "SamirTray"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def generate_status_icon(status: str):
    """توليد أيقونة سمير مع مؤشر لون ديناميكي حي"""
    base_img = None
    if os.path.exists(ICON_PATH):
        try:
            base_img = Image.open(ICON_PATH).convert("RGBA").resize((64, 64))
        except Exception:
            pass

    if base_img is None:
        base_img = Image.new("RGBA", (64, 64), color=(15, 23, 42, 255))
        draw_base = ImageDraw.Draw(base_img)
        # رسم دائرة تمثل سمير
        draw_base.ellipse([8, 8, 56, 56], fill=(0, 229, 255, 255))

    # رسم نقطة الحالة في الزاوية السفلية
    draw = ImageDraw.Draw(base_img)
    color_map = {
        "online": (16, 185, 129, 255),    # أخضر زمردي
        "starting": (245, 158, 11, 255),  # أصفر برتقالي
        "offline": (239, 68, 68, 255)     # أحمر تحذيري
    }
    badge_color = color_map.get(status, (156, 163, 175, 255))

    # حلقة بيضاء خارجية حول النقطة
    draw.ellipse([42, 42, 62, 62], fill=(255, 255, 255, 255))
    draw.ellipse([44, 44, 60, 60], fill=badge_color)

    return base_img


def start_server_if_needed():
    global server_status
    if is_server_ready():
        server_status = "online"
        return True

    server_status = "starting"
    py_exe = VENV_PYTHONW if os.path.exists(VENV_PYTHONW) else (VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable)
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        subprocess.Popen(
            [py_exe, RUN_SERVER],
            cwd=CORE_DIR,
            creationflags=creation_flags,
            close_fds=True,
        )
    except Exception as e:
        server_status = "offline"
        return False

    for _ in range(20):
        time.sleep(0.5)
        if is_server_ready():
            server_status = "online"
            return True

    server_status = "offline"
    return False


def find_browser_app_executable():
    candidates = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def open_samir_window(icon=None, item=None):
    start_server_if_needed()
    browser = find_browser_app_executable()
    if browser:
        args = [
            browser,
            f"--app={APP_URL}",
            "--app-id=samir-ai-assistant",
            "--window-size=1300,880",
            "--window-position=100,50",
        ]
        subprocess.Popen(args)
    else:
        webbrowser.open(APP_URL)


def open_downloads_folder(icon=None, item=None):
    user_home = os.path.expanduser("~")
    downloads = os.path.join(user_home, "Downloads")
    if os.path.exists(downloads):
        os.startfile(downloads)


def open_workspace_folder(icon=None, item=None):
    if os.path.exists(BASE_DIR):
        os.startfile(BASE_DIR)


def restart_server(icon=None, item=None):
    global server_status
    server_status = "starting"
    if icon:
        icon.icon = generate_status_icon("starting")
        icon.title = "سمير الذكي - جاري إعادة التشغيل 🟡"

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"], capture_output=True)
        time.sleep(1)
        if start_server_if_needed():
            if icon:
                icon.icon = generate_status_icon("online")
                icon.title = "سمير الذكي - شغال وجاهز 🟢"
                icon.notify("تم إعادة تشغيل خادم سمير بنجاح! 🟢", "سمير الذكي (Samir AI)")
        else:
            if icon:
                icon.icon = generate_status_icon("offline")
                icon.title = "سمير الذكي - متوقف 🔴"
    except Exception:
        pass


def stop_server_only(icon=None, item=None):
    global server_status
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"], capture_output=True)
        server_status = "offline"
        if icon:
            icon.icon = generate_status_icon("offline")
            icon.title = "سمير الذكي - متوقف مؤقتاً 🔴"
            icon.notify("تم إيقاف خادم سمير مؤقتاً 🔴", "سمير الذكي (Samir AI)")
    except Exception:
        pass


def check_status_now(icon=None, item=None):
    global server_status
    ready = is_server_ready()
    server_status = "online" if ready else "offline"
    if icon:
        icon.icon = generate_status_icon(server_status)
        emoji = "🟢" if ready else "🔴"
        icon.title = f"سمير الذكي - {('متصل وشغال' if ready else 'متوقف')} {emoji}"
        msg = "سمير متصل وجاهز للعمل! 🟢" if ready else "الخادم غير متصل حالياً 🔴"
        try:
            icon.notify(msg, "فحص حالة سمير")
        except Exception:
            pass


def quit_samir(icon, item):
    if icon:
        icon.stop()
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"], capture_output=True)
    except Exception:
        pass
    sys.exit(0)


def monitor_thread(icon):
    """فحص دوري لحالة الخادم وتحديث مؤشر Tray تلقائياً كل 10 ثوان مع الإنعاش التلقائي 24/7"""
    global server_status
    prev_status = None
    offline_counter = 0
    while True:
        try:
            time.sleep(10)
            ready = is_server_ready()
            if not ready:
                offline_counter += 1
                if offline_counter >= 2:
                    # إنعاش تلقائي فوري للخادم لضمان العمل 24 ساعة
                    start_server_if_needed()
                    offline_counter = 0
                    ready = is_server_ready()
            else:
                offline_counter = 0

            current = "online" if ready else "offline"
            if current != prev_status:
                prev_status = current
                server_status = current
                icon.icon = generate_status_icon(current)
                emoji = "🟢" if ready else "🔴"
                icon.title = f"سمير الذكي - {('متصل وجاهز 24/7' if ready else 'متوقف')} {emoji}"
        except Exception:
            pass


def get_status_label(item=None):
    global server_status
    if server_status == "online":
        return "● الحالة: متصل وشغال 🟢"
    elif server_status == "starting":
        return "● الحالة: جاري البدء... 🟡"
    return "● الحالة: متوقف 🔴"


def create_tray_app():
    global tray_icon_instance, server_status
    start_server_if_needed()

    if not HAS_PYSTRAY:
        open_samir_window()
        return

    init_img = generate_status_icon("online" if is_server_ready() else "starting")

    menu = pystray.Menu(
        pystray.MenuItem(get_status_label, check_status_now, enabled=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("فتح سمير (Open Samir)", open_samir_window, default=True),
        pystray.MenuItem("فحص الاتصال الآن (Check Status)", check_status_now),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("فتح مجلد التحميلات (Downloads)", open_downloads_folder),
        pystray.MenuItem("مجلد مشروع سمير (Workspace)", open_workspace_folder),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("إعادة تشغيل الخادم (Restart)", restart_server),
        pystray.MenuItem("إيقاف الخادم (Stop Server)", stop_server_only),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("خروج تماماً (Exit Samir)", quit_samir),
    )

    icon = pystray.Icon("Samir_AI_Assistant", init_img, "سمير الذكي - في الخلفية 🟢", menu)
    tray_icon_instance = icon

    def on_ready(ico):
        # بدء مراقبة الخادم دورياً
        t = threading.Thread(target=monitor_thread, args=(ico,), daemon=True)
        t.start()
        try:
            ico.notify("سمير يعمل الآن في الخلفية وجاهز لخدمتك 🟢", "سمير الذكي (Samir AI)")
        except Exception:
            pass

    icon.run(setup=on_ready)


if __name__ == "__main__":
    create_tray_app()
