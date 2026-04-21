@echo off
setlocal EnableDelayedExpansion
title Cadence — Build
color 0A

echo.
echo  ============================================================
echo   Cadence  —  Build Pipeline
echo   Produces:  dist\Cadence\Cadence.exe   (portable folder)
echo              dist\Cadence_Setup_1.0.0.exe  (installer, if
echo              Inno Setup 6 is installed)
echo  ============================================================
echo.

cd /d "%~dp0"

:: ── 1. Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Install Python 3.10+ from https://www.python.org/downloads/
    echo         and tick "Add Python to PATH".
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v

:: ── 2. Install / upgrade build dependencies ──────────────────────────────────
echo.
echo [STEP 1/4]  Installing build dependencies...
pip install --quiet --upgrade ^
    pyinstaller>=6.0 ^
    pystray ^
    Pillow ^
    openpyxl ^
    flask ^
    reportlab ^
    msal ^
    requests
if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )
echo [OK] Dependencies up to date.

:: ── 3. Generate icon ─────────────────────────────────────────────────────────
echo.
echo [STEP 2/4]  Generating icon...
python create_icon.py
if errorlevel 1 ( echo [ERROR] Icon generation failed. & pause & exit /b 1 )
echo [OK] static\icon.ico ready.

:: ── 4. PyInstaller ───────────────────────────────────────────────────────────
echo.
echo [STEP 3/4]  Building Cadence.exe with PyInstaller (60-120 sec)...
echo             Please wait...
pyinstaller cadence.spec --clean --noconfirm
if errorlevel 1 ( echo [ERROR] PyInstaller build failed. & pause & exit /b 1 )
echo [OK] dist\Cadence\Cadence.exe ready.

:: ── 5. Inno Setup installer ──────────────────────────────────────────────────
echo.
echo [STEP 4/4]  Looking for Inno Setup 6...

set "ISCC="
:: Check PATH first
where iscc >nul 2>&1 && set "ISCC=iscc"

:: Common install locations
if not defined ISCC (
    for %%p in (
        "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
        "%ProgramFiles%\Inno Setup 6\ISCC.exe"
        "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    ) do (
        if exist %%p ( set "ISCC=%%~p" & goto :found_iscc )
    )
)
:found_iscc

if not defined ISCC (
    echo [SKIP]  Inno Setup not found — skipping installer creation.
    echo.
    echo         To create a one-click installer:
    echo           1. Download Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo           2. Install it, then re-run this build.bat
    echo.
    echo         Portable app is still ready at:
    echo           dist\Cadence\Cadence.exe
    goto :done
)

echo [OK] Found: %ISCC%
echo        Compiling cadence.iss...
"%ISCC%" cadence.iss
if errorlevel 1 ( echo [ERROR] Inno Setup compilation failed. & pause & exit /b 1 )
echo [OK] Installer ready at: dist\Cadence_Setup_1.0.0.exe

:done
echo.
echo  ============================================================
echo   Build complete!
echo.
echo   Portable app :  dist\Cadence\Cadence.exe
if defined ISCC (
echo   Installer    :  dist\Cadence_Setup_1.0.0.exe
)
echo  ============================================================
echo.
pause
