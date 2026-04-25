@echo off
setlocal EnableDelayedExpansion
title Cadence — Build
color 0A

cd /d "%~dp0"

:: ── Read version from version.py ─────────────────────────────────────────────
for /f "tokens=*" %%v in ('python -c "from version import __version__; print(__version__)"') do set APP_VERSION=%%v
if not defined APP_VERSION ( echo [ERROR] Could not read version from version.py. & pause & exit /b 1 )

echo.
echo  ============================================================
echo   Cadence  v%APP_VERSION%  —  Build Pipeline
echo   Produces:  dist\Cadence\Cadence.exe   (portable folder)
echo              dist\Cadence_Setup_%APP_VERSION%.exe  (installer)
echo  ============================================================
echo.

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
echo [STEP 1/5]  Installing build dependencies...
pip install --quiet --upgrade ^
    pyinstaller>=6.0 ^
    pystray ^
    Pillow ^
    openpyxl ^
    flask ^
    reportlab ^
    msal ^
    requests ^
    waitress
if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )
echo [OK] Dependencies up to date.

:: ── 3. Generate icon ─────────────────────────────────────────────────────────
echo.
echo [STEP 2/5]  Generating icon...
python create_icon.py
if errorlevel 1 ( echo [ERROR] Icon generation failed. & pause & exit /b 1 )
echo [OK] static\icon.ico ready.

:: ── 4. Generate Windows version resource ─────────────────────────────────────
echo.
echo [STEP 3/5]  Generating file_version_info.txt for v%APP_VERSION%...
python generate_version_info.py
if errorlevel 1 ( echo [ERROR] Version info generation failed. & pause & exit /b 1 )

:: ── 5. PyInstaller ───────────────────────────────────────────────────────────
echo.
echo [STEP 4/5]  Building Cadence.exe with PyInstaller (60-120 sec)...
echo             Please wait...
pyinstaller cadence.spec --clean --noconfirm
if errorlevel 1 ( echo [ERROR] PyInstaller build failed. & pause & exit /b 1 )
echo [OK] dist\Cadence\Cadence.exe ready.

:: ── 6. Inno Setup installer ──────────────────────────────────────────────────
echo.
echo [STEP 5/5]  Looking for Inno Setup 6...

set "ISCC="
where iscc >nul 2>&1 && set "ISCC=iscc"

if not defined ISCC (
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command ^
        "$found = $null; " ^
        "$drives = (Get-PSDrive -PSProvider FileSystem).Root; " ^
        "$username = $env:USERNAME; " ^
        "foreach ($d in $drives) { " ^
            "$paths = @(" ^
                "'${d}Users\\$username\\AppData\\Local\\Programs\\Inno Setup 6\\ISCC.exe'," ^
                "'${d}Program Files\\Inno Setup 6\\ISCC.exe'," ^
                "'${d}Program Files (x86)\\Inno Setup 6\\ISCC.exe'" ^
            "); " ^
            "foreach ($p in $paths) { if (Test-Path $p) { $found = $p; break } } " ^
            "if ($found) { break } " ^
        "} " ^
        "if ($found) { $found } else { '' }"`) do (
        if not "%%i"=="" ( set "ISCC=%%i" )
    )
)

if not defined ISCC (
    echo [SKIP]  Inno Setup not found — skipping installer creation.
    echo.
    echo         To create a one-click installer:
    echo           1. Download Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo           2. Install it, then re-run this build.bat
    echo.
    echo         Portable app is still ready at:  dist\Cadence\Cadence.exe
    goto :done
)

echo [OK] Found: %ISCC%
echo        Compiling cadence.iss for v%APP_VERSION%...
"%ISCC%" /DAppVersion=%APP_VERSION% cadence.iss
if errorlevel 1 ( echo [ERROR] Inno Setup compilation failed. & pause & exit /b 1 )
echo [OK] Installer ready at: dist\Cadence_Setup_%APP_VERSION%.exe

:done
echo.
echo  ============================================================
echo   Build complete!  v%APP_VERSION%
echo.
echo   Portable app :  dist\Cadence\Cadence.exe
if defined ISCC (
echo   Installer    :  dist\Cadence_Setup_%APP_VERSION%.exe
)
echo  ============================================================
echo.
pause
