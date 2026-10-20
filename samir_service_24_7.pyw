"""
Samir AI Assistant - 24/7 Dedicated Background Service & Watchdog
خادم سمير الذكي - خدمة المراقبة والتشغيل الدائم على مدار 24 ساعة دون انقطاع
"""

import os
import sys
import time
import ctypes
import subprocess
import urllib.request
import urllib.error
import logging
from pathlib import Path

# إعداد المسارات
BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / "core_server"
DATA_DIR = CORE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "service_24_7.log"

VENV_PYTHONW = CORE_DIR / ".venv" / "Scripts" / "pythonw.exe"
VENV_PYTHON = CORE_DIR / ".venv" / "Scripts" / "python.exe"
RUN_SERVER = CORE_DIR / "run_server.py"

PORT = 8000
HEALTH_URL = f"http://127.0.0.1:{PORT}/health"
CHECK_INTERVAL_SECONDS = 10
MAX_FAILS_BEFORE_RESTART = 3
BOOT_GRACE_PERIOD_SECONDS = 12

# إعداد السجل (Log) مع تدوير بسيط إذا زاد الحجم عن 5 ميجابايت
if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
    try:
        backup = DATA_DIR / "service_24_7.old.log"
        if backup.exists():
            backup.unlink()
        LOG_FILE.rename(backup)
    except Exception:
        pass

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("Samir24_7")


def prevent_windows_sleep():
    """
    إبلاغ نواة ويندوز بأن السيرفر يعمل كخدمة خلفية حرجة
    يسمح بإطفاء الشاشة لتوفير الطاقة ولكن يمنع تعليق النظام أو النوم (Sleep/Standby)
    """
    try:
        if sys.platform == "win32":
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_AWAYMODE_REQUIRED = 0x00000040
            res = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            )
            if res != 0:
                logger.info("Windows Sleep Prevention enabled: System & AwayMode active.")
            else:
                logger.warning("Could not set Windows execution state.")
    except Exception as e:
        logger.warning(f"Error enabling sleep prevention: {e}")


def ensure_single_instance():
    """ضمان عدم تشغيل أكثر من نسخة واحدة من خدمة المراقبة 24/7"""
    if sys.platform == "win32":
        try:
            mutex_name = "Global\\Samir_24_7_Supervisor_Mutex"
            mutex = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
            last_error = ctypes.windll.kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183
            if last_error == ERROR_ALREADY_EXISTS:
                logger.warning("Another instance of Samir 24/7 Service is already running. Exiting.")
                sys.exit(0)
            return mutex
        except Exception as e:
            logger.warning(f"Mutex creation warning: {e}")
    return None


def get_python_exe() -> str:
    if VENV_PYTHONW.exists():
        return str(VENV_PYTHONW)
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def is_server_healthy() -> bool:
    try:
        req = urllib.request.Request(
            HEALTH_URL,
            headers={"User-Agent": "Samir24_7Watchdog"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def kill_port_8000():
    """إنهاء أي عملية عالقة أو ميتة على المنفذ 8000 لضمان إمكانية الربط"""
    try:
        cmd = f"powershell -NoProfile -Command \"Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}\""
        subprocess.run(cmd, shell=True, capture_output=True)
    except Exception as e:
        logger.warning(f"Error killing port {PORT}: {e}")


def start_server_process():
    """تشغيل خادم سمير في عملية منفصلة تماماً ومخفية في الخلفية"""
    py_exe = get_python_exe()
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | 0x08000000  # CREATE_NO_WINDOW
        )

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        logger.info(f"Starting Samir server process via {py_exe}...")
        proc = subprocess.Popen(
            [py_exe, str(RUN_SERVER)],
            cwd=str(CORE_DIR),
            creationflags=creation_flags,
            close_fds=True,
            env=env
        )
        logger.info(f"Samir server process spawned (PID: {proc.pid}).")
        return proc
    except Exception as e:
        logger.error(f"Failed to spawn Samir server: {e}")
        return None


def main():
    logger.info("=" * 60)
    logger.info("  SAMIR 24/7 BACKGROUND SERVICE STARTED")
    logger.info("=" * 60)

    _mutex = ensure_single_instance()
    prevent_windows_sleep()

    fail_count = 0

    # الفحص المبدئي والتشغيل إذا لم يكن السيرفر يعمل
    if not is_server_healthy():
        logger.info("Initial check: Server is offline. Starting server now...")
        kill_port_8000()
        start_server_process()
        time.sleep(BOOT_GRACE_PERIOD_SECONDS)
    else:
        logger.info("Initial check: Server is already online and healthy 🟢")

    last_sleep_prevention_ping = time.time()
    last_heartbeat_log = time.time()

    while True:
        try:
            # تجديد منع الخمول كل 15 دقيقة لضمان عدم إلغائه من قبل النظام
            if time.time() - last_sleep_prevention_ping > 900:
                prevent_windows_sleep()
                last_sleep_prevention_ping = time.time()

            # تسجيل نبضة حياة كل ساعة للتأكيد في السجل
            if time.time() - last_heartbeat_log > 3600:
                logger.info("Heartbeat: Samir 24/7 service is running smoothly. All systems operational 🟢")
                last_heartbeat_log = time.time()

            if is_server_healthy():
                if fail_count > 0:
                    logger.info("Samir server has recovered and is healthy! 🟢")
                fail_count = 0
            else:
                fail_count += 1
                logger.warning(f"Samir server health check failed ({fail_count}/{MAX_FAILS_BEFORE_RESTART})")

                if fail_count >= MAX_FAILS_BEFORE_RESTART:
                    logger.error("Restart threshold reached! Reviving Samir server...")
                    kill_port_8000()
                    time.sleep(1)
                    start_server_process()
                    fail_count = 0
                    time.sleep(BOOT_GRACE_PERIOD_SECONDS)

            time.sleep(CHECK_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Unexpected error in watchdog loop: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
