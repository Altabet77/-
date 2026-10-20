@echo off
chcp 65001 > nul
title Samir AI - Stop Server
echo ===================================================
echo   إيقاف خادم سمير الذكي (Samir AI Core Hub)
echo ===================================================

echo جارٍ البحث عن العمليات العاملة على المنفذ 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo تم العثور على العملية PID: %%a - جارٍ الإيقاف...
    taskkill /F /PID %%a > nul 2>&1
)

echo.
echo تم إيقاف سمير بنجاح.
timeout /t 2 > nul
