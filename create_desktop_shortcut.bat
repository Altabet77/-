@echo off
chcp 65001 >nul
echo جاري إنشاء اختصار سمير على سطح المكتب...

set "TARGET_BAT=%~dp0launch_samir.bat"
set "ICON_FILE=%~dp0core_server\web_console\favicon.ico"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\سمير — J.A.R.V.I.S AI.lnk"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_BAT%'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = '%ICON_FILE%'; $s.Description = 'سمير — المساعد الشخصي الذكي الخارق (J.A.R.V.I.S)'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [✓] تم إنشاء أيقونة سمير على سطح المكتب بنجاح!
) else (
    echo [!] تعذر إنشاء الأيقونة تلقائياً.
)
timeout /t 3 >nul
