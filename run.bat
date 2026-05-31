@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo App exited with an error. Run install.bat if you haven't already.
    pause
)
