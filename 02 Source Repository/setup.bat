@echo off
title AssureX Claim Engine - Setup
setlocal
cd /d "%~dp0"

echo =====================================================================
echo    AssureX Claim Engine - Environment Setup
echo =====================================================================
echo.

set "SYS_PYTHON="
py -3.11 --version >nul 2>&1 && set "SYS_PYTHON=py -3.11"
if not defined SYS_PYTHON (
    py --version >nul 2>&1 && set "SYS_PYTHON=py"
)
if not defined SYS_PYTHON (
    python --version >nul 2>&1 && set "SYS_PYTHON=python"
)
if not defined SYS_PYTHON (
    if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
        set "SYS_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    )
)

if not defined SYS_PYTHON (
    echo [ERROR] No working Python installation found.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/2] Creating virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    %SYS_PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment (.venv) already exists.
)

echo.
echo [2/2] Installing dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation encountered an issue.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo Setup complete! You can now run run_app.bat to start AssureX.
echo =====================================================================
pause
