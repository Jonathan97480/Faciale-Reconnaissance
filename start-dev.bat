@echo off
REM Script Windows pour lancer backend et frontend en parallèle
start "BACKEND" cmd /k "cd backend && ..\.venv\Scripts\activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "FRONTEND" cmd /k "cd frontend && npm run dev"
