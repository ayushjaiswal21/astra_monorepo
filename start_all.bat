@echo off
title Monorepo Starter

echo Starting AI Guru backend (FastAPI)...
start "AI Guru Backend" cmd /k "cd ai-guru\backend && python main.py"

echo Starting Astra Authentication app (Flask)...
start "Astra Auth App" cmd /k "cd asta_authentication && python app.py"

echo Starting Astra modules (Django)...
start "Astra Modules" cmd /k "cd astra && python manage.py runserver"

echo All projects are starting in separate windows.