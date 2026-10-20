@echo off
setlocal
set "BASE_DIR=%~dp0"
set "PY_EXE=%BASE_DIR%core_server\.venv\Scripts\pythonw.exe"
if not exist "%PY_EXE%" set "PY_EXE=pythonw.exe"

start "" "%PY_EXE%" "%BASE_DIR%launch_samir.pyw"
exit
