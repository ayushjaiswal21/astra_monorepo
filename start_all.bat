@echo off
title Monorepo Service Starter

echo ====================================================================
echo  Astra Monorepo Service Starter
echo ====================================================================
echo.
echo IMPORTANT PREREQUISITES:
echo 1. Make sure your Redis server is running. Celery depends on it.
echo 2. Ensure you have created and configured your .env files for:
echo    - astra/
echo    - ai-guru/backend/
echo    (Based on the .env.example files if they exist)
echo 3. Make sure all dependencies are installed for each project:
echo    - pip install -r requirements.txt (for each Python project)
echo    - npm install (for the frontend project)
echo.
echo This script will open a new window for each service.
echo Please keep them running.
echo.

echo Starting services...
echo.

echo [1/5] Starting Astra Authentication (Flask on port 5000)...
start "Astra Auth" cmd /k "cd asta_authentication && python app.py"

echo [2/5] Starting AI Guru Backend (FastAPI on port 8001)...
start "AI Guru Backend" cmd /k "cd ai-guru && python -m uvicorn backend.main:app --port 8001"

echo [3/5] Starting AI Guru Frontend (React on port 3000)...
start "AI Guru Frontend" cmd /k "cd ai-guru\frontend && npm install && npm start"

echo [4/5] Starting Astra Platform (Django on port 8000)...
start "Astra Platform" cmd /k "cd astra && python manage.py migrate && python manage.py runserver"

echo [5/5] Starting Astra Celery Worker...
start "Astra Celery Worker" cmd /k "cd astra && celery -A astralearn worker -l info"

echo.
echo ====================================================================
echo  All services are starting up in separate windows.
echo ====================================================================
echo.
echo Please check the individual windows for status and errors.
echo.
echo Access the applications at:
echo   - Astra Authentication: http://127.0.0.1:5000
echo   - AI Guru Frontend:     http://localhost:3000
echo   - Astra Platform:       http://127.0.0.1:8000
echo.
echo This window will close in 15 seconds...
timeout /t 15 >nul