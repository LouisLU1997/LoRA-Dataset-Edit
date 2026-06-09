@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python not found.
    echo  Please install Python 3.10 or 3.11 from:
    echo  https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo Checking dependencies...
python -m pip install --quiet --disable-pip-version-check pillow send2trash fastapi uvicorn python-multipart

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7788 ^| findstr LISTENING') do (
    echo Killing existing process on port 7788 ^(PID %%a^)...
    taskkill /PID %%a /F >nul 2>&1
)

python main_web.py
