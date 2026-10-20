"""
Samir AI Assistant - 24/7 Autostart Manager
إدارة التشغيل التلقائي مع بدء تشغيل ويندوز وضمان العمل 24 ساعة
"""

import os
import sys
import winreg
import subprocess
from pathlib import Path

# Fix console encoding for Arabic
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / "core_server"
SERVICE_PYW = BASE_DIR / "samir_service_24_7.pyw"
VENV_PYTHONW = CORE_DIR / ".venv" / "Scripts" / "pythonw.exe"
ICON_PATH = BASE_DIR / "samir.ico"

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "Samir_24_7_Service"


def get_pythonw():
    if VENV_PYTHONW.exists():
        return str(VENV_PYTHONW)
    return "pythonw.exe"


def get_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_shortcut_path() -> Path:
    return get_startup_folder() / "Samir_24_7_Service.lnk"


def enable_autostart() -> bool:
    print("=" * 60)
    print("⚡ تفعيل تشغيل سمير 24/7 تلقائياً مع بدء تشغيل ويندوز")
    print("=" * 60)

    pyw = get_pythonw()
    cmd = f'"{pyw}" "{SERVICE_PYW}"'

    # 1. إضافة إلى Windows Registry (Run)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print(" [✓] تم تسجيل الخدمة بنجاح في سجل ويندوز (Windows Registry Run)")
    except Exception as e:
        print(f" [!] خطأ في تسجيل Registry: {e}")

    # 2. إنشاء اختصار مباشر في مجلد بدء التشغيل (Startup Folder) كطبقة أمان إضافية
    try:
        startup_lnk = get_shortcut_path()
        ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{str(startup_lnk)}")
$s.TargetPath = "{pyw}"
$s.Arguments = '"{str(SERVICE_PYW)}"'
$s.WorkingDirectory = "{str(BASE_DIR)}"
$s.IconLocation = "{str(ICON_PATH)}"
$s.Description = "Samir AI Assistant 24/7 Background Service"
$s.Save()
"""
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True)
        if startup_lnk.exists():
            print(" [✓] تم إنشاء اختصار في مجلد بدء التشغيل (Startup Folder)")
    except Exception as e:
        print(f" [!] خطأ في إنشاء اختصار Startup: {e}")

    # 3. تشغيل الخدمة فوراً في الخلفية إذا لم تكن قيد التشغيل
    try:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000
        subprocess.Popen([pyw, str(SERVICE_PYW)], cwd=str(BASE_DIR), creationflags=flags, close_fds=True)
        print(" [✓] تم إطلاق خدمة المراقبة 24/7 في الخلفية بنجاح!")
    except Exception as e:
        print(f" [!] خطأ في إطلاق الخدمة: {e}")

    print("\n✅ تم بنجاح! سمير الآن سيعمل 24 ساعة ولن يتوقف أبداً حتى بعد إعادة تشغيل الكمبيوتر.")
    return True


def disable_autostart() -> bool:
    print("=" * 60)
    print("🛑 إلغاء التشغيل التلقائي لخادم سمير 24/7")
    print("=" * 60)

    # 1. إزالة من Windows Registry
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        print(" [✓] تم حذف الخدمة من سجل ويندوز (Windows Registry)")
    except FileNotFoundError:
        print(" [-] الخدمة غير مسجلة مسبقاً في Registry.")
    except Exception as e:
        print(f" [!] خطأ أثناء الحذف من Registry: {e}")

    # 2. إزالة الاختصار من مجلد Startup
    try:
        shortcut = get_shortcut_path()
        if shortcut.exists():
            shortcut.unlink()
            print(" [✓] تم حذف اختصار مجلد بدء التشغيل (Startup Folder)")
    except Exception as e:
        print(f" [!] خطأ أثناء حذف الاختصار: {e}")

    # 3. إيقاف عملية المراقبة
    try:
        ps_cmd = 'Get-WmiObject Win32_Process | Where-Object { ($_.Name -like "python*.exe") -and ($_.CommandLine -like "*samir_service_24_7.pyw*") } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        print(" [✓] تم إيقاف خدمة المراقبة 24/7 في الخلفية.")
    except Exception as e:
        print(f" [!] خطأ أثناء إيقاف الخدمة: {e}")

    print("\n✅ تم إلغاء وضع 24/7 بنجاح.")
    return True


def check_status():
    print("=" * 60)
    print("🔍 فحص حالة سمير 24/7 (Samir 24/7 Status)")
    print("=" * 60)

    # 1. فحص Registry
    reg_ok = False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg_ok = True
    except Exception:
        pass

    # 2. فحص مجلد Startup
    shortcut_ok = get_shortcut_path().exists()

    # 3. فحص هل خدمة 24/7 تعمل حالياً في الخلفية
    ps_cmd = 'Get-WmiObject Win32_Process | Where-Object { ($_.Name -like "python*.exe") -and ($_.CommandLine -like "*samir_service_24_7.pyw*") } | Select-Object -ExpandProperty ProcessId'
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    pids = [p.strip() for p in res.stdout.splitlines() if p.strip()]
    service_running = len(pids) > 0

    # 4. فحص هل السيرفر يعمل على منفذ 8000
    server_online = False
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1.5) as r:
            server_online = (r.status == 200)
    except Exception:
        pass

    # 5. جلب رابط النفق إن وجد
    tunnel_file = BASE_DIR / "tunnel_url.txt"
    tunnel_url = None
    if tunnel_file.exists():
        try:
            t = tunnel_file.read_text(encoding="utf-8").strip()
            if t.startswith("https://"):
                tunnel_url = t
        except Exception:
            pass

    print(f"● التشغيل التلقائي مع ويندوز (Registry) : {'🟢 مفعل (Enabled)' if reg_ok else '🔴 غير مفعل (Disabled)'}")
    print(f"● اختصار مجلد Startup                : {'🟢 موجود (Present)' if shortcut_ok else '🔴 غير موجود'}")
    print(f"● خدمة المراقبة 24/7 (Watchdog)       : {'🟢 تعمل بنجاح (PID: ' + ', '.join(pids) + ')' if service_running else '🔴 متوقفة'}")
    print(f"● خادم سمير المركزي (Port 8000)       : {'🟢 شغال وجاهز (Healthy)' if server_online else '🔴 متوقف'}")
    if tunnel_url:
        print(f"● رابط الهاتف الخارجي (Cloudflare)    : 🌐 {tunnel_url}")
    print("=" * 60)


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "status"
    if action in ("enable", "install", "on"):
        enable_autostart()
    elif action in ("disable", "uninstall", "off"):
        disable_autostart()
    else:
        check_status()
