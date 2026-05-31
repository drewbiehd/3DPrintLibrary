@echo off
echo ========================================
echo   3D Print Library - Setup
echo ========================================
echo.

:: Check for Python
where python >nul 2>&1
if errorlevel 1 (
    echo Python not found!
    echo Please install Python 3.11 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

python --version
echo.
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Installation failed. Try running as Administrator.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation complete!
echo   Run "run.bat" to start the app.
echo ========================================
pause
