@echo off
title Cadence Setup
echo ============================================
echo  Cadence - First Time Setup
echo ============================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Please install Python 3.10 or later from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
echo.
pip install -r "%~dp0requirements.txt"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed. Please check the error above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Setup complete!
echo  Run launch.bat to start (developer mode).
echo  Run build.bat to create a standalone .exe.
echo ============================================
pause
