@echo off
chcp 65001 > nul
title Samir AI - فحص حالة الخادم 24/7
color 0B

echo ===================================================
echo 🤖 فحص حالة مساعد سمير الذكي (Samir AI Status)
echo ===================================================
echo.

set "PY=%~dp0core_server\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python.exe"

set PYTHONIOENCODING=utf-8
"%PY%" "%~dp0manage_autostart.py" status

echo.
echo اضغط أي مفتاح للإنهاء...
pause > nul
