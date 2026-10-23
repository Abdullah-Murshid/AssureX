@echo off
REM AssureX Claim Engine - REST API (Django Ninja)
REM Serves the API on http://127.0.0.1:8011/api/docs
cd /d "%~dp0"
uv run python backend\manage.py runserver 8011
