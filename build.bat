@echo off
title Cadence — Build
echo ============================================
echo  Cadence - Build Standalone App
echo ============================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Run setup.bat first.
    pause & exit /b 1
)

:: Install build dependencies
echo Installing build dependencies...
pip install pyinstaller pystray Pillow --quiet
if errorlevel 1 ( echo ERROR: pip failed. & pause & exit /b 1 )

:: Generate icon
echo Generating icon...
python create_icon.py
if errorlevel 1 ( echo ERROR: Icon generation failed. & pause & exit /b 1 )

:: Build
echo.
echo Building Cadence.exe (this takes ~60 seconds)...
pyinstaller cadence.spec --clean --noconfirm
if errorlevel 1 ( echo ERROR: PyInstaller failed. & pause & exit /b 1 )

echo.
echo ============================================
echo  Build complete!
echo  Your app is in:  dist\Cadence\
echo  Double-click:    dist\Cadence\Cadence.exe
echo ============================================
pause
