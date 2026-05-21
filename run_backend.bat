@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Virtual environment not found. Run setup.bat first.
  pause
  exit /b
)
call .venv\Scripts\activate
python3 -m uvicorn backend.main:app --reload
pause
