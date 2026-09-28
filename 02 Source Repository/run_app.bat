@echo off
title AssureX Claim Engine - Server Launcher
setlocal
cd /d "%~dp0"

echo =====================================================================
echo    AssureX Claim Engine - Enterprise AI Warranty Adjudication Platform
echo =====================================================================
echo.

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "..\.venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\..\.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "..\..\.runtime\Scripts\python.exe" set "PYTHON_EXE=%CD%\..\..\.runtime\Scripts\python.exe"
if not defined PYTHON_EXE if exist "..\..\techwiz-main\.venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\..\..\techwiz-main\.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
  echo [ERROR] Python environment not found. Please run setup.bat first.
  pause
  exit /b 1
)

echo [1/2] Verifying Python environment...
"%PYTHON_EXE%" -c "import fastapi,sqlalchemy,xgboost" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] The Python environment is incomplete. Please run setup.bat.
  pause
  exit /b 1
)

echo [2/2] Launching server at http://127.0.0.1:8000 ...
echo [INFO] Browser will open automatically in 1-2 seconds.
echo.

"%PYTHON_EXE%" launch.py
if errorlevel 1 pause

