@echo off
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
start /B npm start
timeout /t 2 /nobreak

echo.
echo ========================================
echo   ✓ Greenie is starting!
echo ========================================
echo.
echo Look for the GREEN ICON in your system tray.
echo (Bottom-right corner of your screen)
echo.
echo Right-click the green icon to:
echo   • Show the chat window
echo   • Quit the app
echo.
echo You can close this window now.
echo.
pause
exit
