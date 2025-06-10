@echo off
echo Octopus Energy API Data Fetcher Setup
echo ===================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python is installed. Installing dependencies...

REM Install required packages
pip install -r requirements.txt

if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.
echo To use the scripts:
echo 1. Set your environment variables:
echo    set OCTOPUS_API_KEY=your_actual_api_key
echo    set OCTOPUS_ACCOUNT_NUMBER=A-AAAA1111
echo.
echo 2. Test public API (no auth required):
echo    python octopus_api_example.py
echo.
echo 3. Fetch your consumption data:
echo    python octopus_energy_fetcher.py
echo.

pause 