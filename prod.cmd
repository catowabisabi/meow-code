@echo off
title AI Code Assistant - PRODUCTION
echo ========================================
echo   AI Code Assistant - Production Mode
echo ========================================
echo.

set ROOT=%~dp0

:: Initialize conda for this cmd session
call C:\Users\enoma\miniconda3\Scripts\activate.bat C:\Users\enoma\miniconda3 2>nul

echo [1/2] Building frontend...
cd /d %ROOT%webui\client
call npm run build
if errorlevel 1 (
    echo.
    echo ERROR: Frontend build failed!
    echo Run "npm install" in webui\client first if dependencies are missing.
    pause
    exit /b 1
)

:: Kill any process already using port 7778
echo Checking for existing process on port 7778...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7778 " ^| findstr "LISTENING"') do (
    echo Killing PID %%a on port 7778...
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo [2/2] Starting API server on port 7778...
echo.
echo ========================================
echo   http://localhost:7778
echo ========================================
echo.

start http://localhost:7778
cd /d %ROOT%
C:\Users\enoma\miniconda3\envs\cato-code\python.exe api_server/run.py
pause
