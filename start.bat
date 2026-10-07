@echo off
rem Starts everything for GeoQuery Sentinel: database + tiles (Docker), backend, frontend.
rem Double-click it, or run "start.bat" from the repo root. Needs Docker Desktop running.
cd /d "%~dp0"

echo [1/3] Starting database and tile server (Docker)...
docker compose up -d
if errorlevel 1 (
    echo.
    echo Docker failed. Is Docker Desktop running? Start it, then run this file again.
    pause
    exit /b 1
)

echo [2/3] Starting backend on http://localhost:8000 ...
start "Sentinel backend" cmd /k "cd /d %~dp0 && app\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"

echo [3/3] Starting frontend (Vite) ...
start "Sentinel frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Started. Two new windows opened (backend, frontend). The frontend prints its URL
echo (usually http://localhost:5173). Run stop.bat when you are done.
