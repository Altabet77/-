@echo off
chcp 65001 > nul
title Samir AI - إلغاء التشغيل الدائم 24/7
color 0C

echo ===================================================
echo 🛑 إلغاء تفعيل نظام سمير الدائم 24/7
echo ===================================================
echo.

set "PY=%~dp0core_server\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python.exe"

set PYTHONIOENCODING=utf-8
"%PY%" "%~dp0manage_autostart.py" disable

echo.
echo اضغط أي مفتاح للإنهاء...
pause > nul
