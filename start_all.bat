@echo off
title Monorepo Starter

echo Starting AI Guru backend (FastAPI)...
start "AI Guru Backend" cmd /k "cd ai-guru\backend && python main.py"

echo Starting AI Guru frontend (React)...
start "AI Guru Frontend" cmd /k "cd ai-guru\frontend && npm start"

echo Starting Astra Authentication app (Flask)...
start "Astra Auth App" cmd /k "cd asta_authentication && python app.py"

echo Starting Astra modules (Django)...
start "Astra Modules" cmd /k "cd astra && python manage.py runserver --noreload --verbosity=0"

echo All projects are starting in separate windows.
echo.
echo AI Guru Backend: http://localhost:8001
echo AI Guru Frontend: http://localhost:3000
echo Astra Authentication: http://localhost:5000
echo Astra Dashboard: http://localhost:8000
echo.
echo Press any key to close this window...
pause >nul