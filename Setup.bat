@echo off
setlocal
cd /d "%~dp0"

echo.
echo Helcyon-Bench setup
echo ===================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    ) else (
        echo Python was not found.
        echo Install Python 3.10 or newer from https://www.python.org/downloads/
        echo Make sure "Add python.exe to PATH" is enabled, then run this setup again.
        echo.
        pause
        exit /b 1
    )
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>nul
    if errorlevel 1 (
        echo Existing .venv is not usable in this folder. Rebuilding it...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 (
        echo.
        echo Failed to create .venv.
        pause
        exit /b 1
    )
) else (
    echo Reusing existing .venv.
)

echo.
echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo.
    echo Failed to update pip tooling.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install Helcyon-Bench dependencies.
    pause
    exit /b 1
)

if not exist "config.yaml" (
    if exist "config.example.yaml" (
        echo.
        echo Creating config.yaml from config.example.yaml...
        copy "config.example.yaml" "config.yaml" >nul
    )
) else (
    echo.
    echo Keeping existing config.yaml.
)

echo.
echo Setup complete.
echo Double-click Run.bat to start Helcyon-Bench.
echo.
pause
