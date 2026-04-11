@echo off
title AI Code Assistant - DEV MODE
echo ========================================
echo   AI Code Assistant - Development Mode
echo ========================================
echo.

set ROOT=%~dp0

:: Initialize conda for this cmd session
call C:\Users\enoma\miniconda3\Scripts\activate.bat C:\Users\enoma\miniconda3 2>nul

echo Checking uvicorn in conda env cato-code...
call conda run -n cato-code python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo uvicorn not found, installing...
    call conda run -n cato-code pip install "uvicorn[standard]"
    if errorlevel 1 (
        echo [ERROR] Failed to install uvicorn. Is conda env "cato-code" set up?
        pause
        exit /b 1
    )
)

:: Kill any process already using port 7778
echo Checking for existing process on port 7778...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7778 " ^| findstr "LISTENING"') do (
    echo Killing PID %%a on port 7778...
    taskkill /PID %%a /F >nul 2>&1
)

echo [1/2] Starting API server (FastAPI) on port 7778...
start "Backend - FastAPI" cmd /k "cd /d %ROOT% && C:\Users\enoma\miniconda3\envs\cato-code\python.exe -m api_server.run"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul
echo [2/2] Starting frontend dev server (Vite HMR) on port 7777...
start "Frontend - Vite" cmd /k "cd /d %ROOT%webui\client && npm run dev"

echo.
echo ========================================
echo   API Server:  http://localhost:7778
echo   Frontend:    http://localhost:7777
echo ========================================
echo.
echo Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:7777
