@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================================
echo    🚀 Launching PetConnect Animal Shelter ML System
echo ==========================================================

if not exist "venv\Scripts\python.exe" (
    echo 📦 Setting up local Python virtual environment...
    if exist venv rmdir /s /q venv
    python -m venv venv
    echo 📥 Installing dependencies from requirements.txt...
    venv\Scripts\pip.exe install -r requirements.txt
)

echo ✅ Environment ready! Launching web server...
call venv\Scripts\activate.bat
python app.py
pause
