@echo off
setlocal
cd /d "%~dp0"

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

if exist "tools\Stop-HelcyonBench.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Stop-HelcyonBench.ps1" -Workspace "%CD%"
)

call ".venv\Scripts\activate.bat"

streamlit run app.py

if exist "tools\Stop-HelcyonBench.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Stop-HelcyonBench.ps1" -Workspace "%CD%"
)

pause
