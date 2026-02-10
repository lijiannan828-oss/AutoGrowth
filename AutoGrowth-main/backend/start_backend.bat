@echo off
echo Starting Backend Server...
cd /d "%~dp0"
python -m uvicorn app.main:app --reload --port 8001
pause

