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
call npm start

pause

