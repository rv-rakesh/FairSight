@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  FairSight FastAPI Backend Launcher (Windows)
echo ============================================================
echo.
echo Starting FairSight AI backend on http://0.0.0.0:8000
echo Local Swagger Docs : http://127.0.0.1:8000/docs
echo Health Check       : http://127.0.0.1:8000/health
echo Android Emulator   : http://10.0.2.2:8000
echo.
echo For physical Android devices on the same Wi-Fi network:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    echo   LAN URL candidate: http://%%a:8000
)
echo   Ensure Windows Firewall allows inbound TCP port 8000 on Private network.
echo.

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m uvicorn api:app --host 0.0.0.0 --port 8000
) else (
    python -m uvicorn api:app --host 0.0.0.0 --port 8000
)
