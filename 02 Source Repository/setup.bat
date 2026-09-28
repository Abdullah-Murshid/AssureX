@echo off
setlocal
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 (
  echo Install 64-bit Python 3.11 with its Windows launcher, then retry.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo Installation complete. Run run_app.bat.
pause
