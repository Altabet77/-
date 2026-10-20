@echo off
chcp 65001 > nul
title Samir AI Assistant Hub (سمير)
echo ===================================================
echo 🤖 تشغيل مساعد سمير الذكي (Samir AI Assistant Hub)
echo ===================================================

cd /d "%~dp0core_server"

if not exist ".venv\Scripts\python.exe" (
    echo ❌ لم يتم العثور على البيئة الافتراضية .venv!
    pause
    exit /b 1
)

echo 🟢 تشغيل خدمة المراقبة الدائمة 24/7 في الخلفية...
start "" ..\core_server\.venv\Scripts\pythonw.exe "..\samir_service_24_7.pyw"

echo 🟢 تشغيل سمير في شريط المهام...
start "" ..\core_server\.venv\Scripts\pythonw.exe "..\samir_tray.pyw"

echo 🌐 فتح واجهة سمير (splash page)...
start "" "%~dp0_samir_loading.html"

echo 🚀 جاري تشغيل السيرفر المركزي (24/7 Active)...
.venv\Scripts\python.exe run_server.py

pause
