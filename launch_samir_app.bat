@echo off
chcp 65001 > nul
title SAMIR — JARVIS Desktop App
color 0B

echo.
echo  ╔══════════════════════════════════════╗
echo  ║    SAMIR AI — JARVIS Protocol v2.0  ║
echo  ║    Starting Desktop Application...  ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0electron_app"

if not exist "node_modules\electron" (
    echo  [*] Installing Electron dependencies...
    powershell -ExecutionPolicy Bypass -Command "npm install" 2>nul
    if errorlevel 1 (
        call npm install
    )
)

echo  [*] Launching SAMIR Desktop App...
echo.
powershell -ExecutionPolicy Bypass -Command "npx electron ."

if errorlevel 1 (
    echo.
    echo  [!] Electron failed. Falling back to browser mode...
    start http://localhost:8000
)
