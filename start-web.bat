@echo off
setlocal
title AetherCraft Web Platform
color 0B
echo ===================================================================
echo   AETHERCRAFT // WEB PLATFORM (FLASK + WAITRESS)
echo   http://127.0.0.1:5000
echo ===================================================================
cd /d "%~dp0web"

set "PYTHON_CMD=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
        if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
        if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
        if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    )
)

"%PYTHON_CMD%" -u app.py
pause
