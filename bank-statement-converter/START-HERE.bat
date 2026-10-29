@echo off
REM Double-click this file to set up and start the Wells Fargo Statement Converter.
cd /d "%~dp0"

echo ============================================
echo  Wells Fargo Statement Converter
echo ============================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo Python is not installed or not on PATH.
        echo.
        echo 1. Go to https://www.python.org/downloads/
        echo 2. Download and run the installer
        echo 3. IMPORTANT: tick "Add python.exe to PATH" on the first screen
        echo 4. Close this window and double-click START-HERE.bat again
        echo.
        start https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

REM First run: create venv + install dependencies
if not exist .venv\Scripts\python.exe (
    echo First-time setup: creating environment and installing packages...
    echo This takes a minute or two.
    echo.
    python -m venv .venv 2>nul || py -m venv .venv
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .venv\Scripts\python.exe -m pip install --quiet pdfplumber pandas openpyxl flask reportlab
    echo Setup complete!
    echo.
)

echo Starting the converter... Your browser will open.
echo Drag and drop your Wells Fargo PDF onto the page.
echo Press Ctrl+C in this window to stop.
echo.
start "" http://localhost:8080
.venv\Scripts\python.exe app.py
pause
