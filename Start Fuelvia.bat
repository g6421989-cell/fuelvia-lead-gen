@echo off
title Fuelvia — Lead Generation Dashboard
color 0A

echo.
echo  ============================================
echo    FUELVIA LEAD GENERATION SYSTEM
echo  ============================================
echo.
echo  Killing any old server on port 5000...

REM Kill any old server
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo  Starting Fuelvia server in new window...

REM Write a temp launcher script to avoid nested-quote issues
set PROJDIR=D:\Chrome Downloads\Claude Powerd Lead Gen system\new lead system
echo @echo off > "%TEMP%\fuelvia_run.bat"
echo title Fuelvia Server - Keep this open! >> "%TEMP%\fuelvia_run.bat"
echo color 0A >> "%TEMP%\fuelvia_run.bat"
echo cd /d "%PROJDIR%" >> "%TEMP%\fuelvia_run.bat"
echo echo. >> "%TEMP%\fuelvia_run.bat"
echo echo  Fuelvia server running at http://127.0.0.1:5000 >> "%TEMP%\fuelvia_run.bat"
echo echo  Password: fuelvia2025 >> "%TEMP%\fuelvia_run.bat"
echo echo  Keep this window open! >> "%TEMP%\fuelvia_run.bat"
echo echo. >> "%TEMP%\fuelvia_run.bat"
echo py app.py >> "%TEMP%\fuelvia_run.bat"

start "Fuelvia Server" cmd /k "%TEMP%\fuelvia_run.bat"

REM Wait for Flask to boot
ping -n 5 127.0.0.1 >nul

REM Open browser
start http://127.0.0.1:5000

echo.
echo  ============================================
echo    Browser opened at 127.0.0.1:5000
echo    Password: fuelvia2025
echo  ============================================
echo.
echo  Keep the GREEN terminal window open.
echo  Close this window now.
echo.
timeout /t 5
