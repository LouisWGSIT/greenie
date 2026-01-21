@echo off
echo Installing Greenie Desktop dependencies...
cd electron
call npm install
echo.
echo Starting Greenie Desktop...
call npm start
pause
