@echo off
title Cadence
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please run setup.bat first.
    pause
    exit /b 1
)

echo Starting Cadence...
start "" pythonw main.py
