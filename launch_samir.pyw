import os, sys, subprocess, urllib.request, webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(BASE_DIR, "core_server")
VENV_PYW = os.path.join(CORE_DIR, ".venv", "Scripts", "pythonw.exe")
VENV_PY  = os.path.join(CORE_DIR, ".venv", "Scripts", "python.exe")
RUN_SERVER = os.path.join(CORE_DIR, "run_server.py")
PORT = 8000
HEALTH_URL = "http://localhost:8000/health"

def _py():
    for p in (VENV_PYW, VENV_PY):
        if os.path.exists(p): return p
    return sys.executable

def _flags():
    if sys.platform == "win32":
        return subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    return 0

def is_ready():
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent":"SamirLauncher"})
        with urllib.request.urlopen(req, timeout=1.5) as r: return r.status == 200
    except: return False

def find_browser():
    for p in [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]:
        if os.path.exists(p): return p
    return None

def open_splash():
    splash_path = os.path.join(BASE_DIR, "_samir_loading.html")
    b = find_browser()
    url = "file:///" + splash_path.replace("\\", "/")
    if b: subprocess.Popen([b, "--app=" + url, "--window-size=1300,880", "--window-position=100,50"])
    else: webbrowser.open(url)

def start_24_7_service():
    svc = os.path.join(BASE_DIR, "samir_service_24_7.pyw")
    if not os.path.exists(svc): return
    try: subprocess.Popen([_py(), svc], cwd=BASE_DIR, creationflags=_flags(), close_fds=True)
    except: pass

def start_server():
    start_24_7_service()
    if is_ready(): return
    subprocess.Popen([_py(), RUN_SERVER], cwd=CORE_DIR, creationflags=_flags(), close_fds=True)

def start_tray():
    t = os.path.join(BASE_DIR, "samir_tray.pyw")
    if not os.path.exists(t): return
    try: subprocess.Popen([_py(), t], cwd=BASE_DIR, creationflags=_flags(), close_fds=True)
    except: pass

if __name__ == "__main__":
    start_24_7_service()
    start_server()
    electron_exe = os.path.join(BASE_DIR, "electron_app", "node_modules", "electron", "dist", "electron.exe")
    electron_dir = os.path.join(BASE_DIR, "electron_app")
    if os.path.exists(electron_exe):
        subprocess.Popen([electron_exe, "."], cwd=electron_dir, creationflags=_flags(), close_fds=True)
    else:
        open_splash()
        start_tray()