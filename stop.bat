@echo off
rem Stops the Docker services and closes the backend and frontend windows opened by start.bat.
cd /d "%~dp0"

echo Closing backend and frontend windows...
taskkill /FI "WINDOWTITLE eq Sentinel backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Sentinel frontend*" /T /F >nul 2>&1

echo Stopping Docker services (data is kept)...
docker compose stop

echo Done.
