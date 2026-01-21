@echo off
setlocal enabledelayedexpansion
cls
echo.
echo ========================================
echo   Greenie Desktop - Starting...
echo ========================================
echo.

cd electron

if not exist node_modules (
    echo Installing dependencies...
    call npm install
    echo.
)

echo Starting Greenie...
echo Launching app in background...

REM Start npm in a separate detached process
start "Greenie Backend" /B cmd /c npm start

REM Give it time to start
timeout /t 2 /nobreak

echo.
echo ========================================
echo   GREENIE IS RUNNING
echo ========================================
echo.
echo Looking for the GREEN ICON in system tray...
echo (Bottom-right corner of your screen)
echo.
echo Right-click the green icon to:
echo   * Show the chat window
echo   * Quit the app
echo.
echo Closing this window WILL NOT stop Greenie.
echo.
echo Press any key to close this startup window...
pause >nul
exit
