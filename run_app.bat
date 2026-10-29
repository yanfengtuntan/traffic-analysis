@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Project virtual environment was not found.
  echo Read README.md and rebuild .venv first.
  pause
  exit /b 1
)

if not exist ".tmp" mkdir ".tmp"
if not exist ".pip-cache" mkdir ".pip-cache"
set "PYTHONIOENCODING=utf-8"
set "PIP_CACHE_DIR=%CD%\.pip-cache"
set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"

echo Starting the traffic analysis application...
echo Open http://localhost:8501 in your browser.
echo Press Ctrl+C in this window to stop the application.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.address localhost --server.port 8501 --browser.gatherUsageStats false

