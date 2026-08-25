@echo off
REM Argus launcher for Windows. Double-click this.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python not found. Install from python.org and tick "Add to PATH". & pause & exit /b 1)
if not exist ".venv" (
  echo First run - setting up...
  python -m venv .venv || (echo venv failed & pause & exit /b 1)
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip >nul
  python -m pip install -r requirements.txt || (echo install failed & pause & exit /b 1)
) else (
  call .venv\Scripts\activate.bat
)
python run.py
pause
