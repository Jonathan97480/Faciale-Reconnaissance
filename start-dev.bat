@echo off
REM Script Windows pour lancer backend et frontend en parallèle
start "BACKEND" cmd /k "cd backend && ..\.venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8001"

REM Attend que l'API backend soit disponible avant de lancer le frontend
powershell -NoProfile -Command ^
  "$ok = $false; for ($i = 0; $i -lt 60; $i++) { try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/openapi.json -TimeoutSec 1 | Out-Null; $ok = $true; break } catch { Start-Sleep -Milliseconds 500 } }; if (-not $ok) { Write-Host 'Backend non disponible sur 8001 apres attente.' }"

start "FRONTEND" cmd /k "cd frontend && npm run dev"
