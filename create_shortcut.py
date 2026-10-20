import os
import subprocess

def create_desktop_shortcut():
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    shortcut_path = os.path.join(desktop, 'Samir - JARVIS AI.lnk')
    pyw_target = os.path.abspath(os.path.join('core_server', '.venv', 'Scripts', 'pythonw.exe'))
    if not os.path.exists(pyw_target):
        pyw_target = "pythonw.exe"
    pyw_script = os.path.abspath('launch_samir.pyw')
    work_dir = os.path.abspath('.')
    icon = os.path.abspath('samir.ico')
    if not os.path.exists(icon):
        icon = os.path.abspath(os.path.join('core_server', 'web_console', 'favicon.ico'))

    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{pyw_target}"
$s.Arguments = '"{pyw_script}"'
$s.WorkingDirectory = "{work_dir}"
$s.IconLocation = "{icon}"
$s.Description = "Samir - JARVIS AI Desktop"
$s.Save()
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    if os.path.exists(shortcut_path):
        print(f"[OK] Desktop shortcut created: {shortcut_path}")
        return True
    else:
        print("[!] فشل إنشاء الاختصار:", res.stderr)
        return False

if __name__ == '__main__':
    create_desktop_shortcut()
