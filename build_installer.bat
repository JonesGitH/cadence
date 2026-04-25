@echo off
"D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 "E:\Code\cadence\cadence.iss"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: dist\Cadence_Setup_1.0.0.exe created.
) else (
    echo.
    echo FAILED with error %ERRORLEVEL%
)
pause
