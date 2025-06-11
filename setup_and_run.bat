@echo off
echo.
echo ======================================
echo   Octopus Energy Dashboard Setup
echo ======================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Python found - checking dependencies...

REM Install required packages
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.

REM Check for API key file
if not exist "oct_api.txt" (
    echo WARNING: No API key file found!
    echo Please create 'oct_api.txt' with your Octopus Energy API key
    echo You can get your API key from your Octopus Energy account dashboard
    echo.
    echo Creating empty oct_api.txt file...
    echo your_api_key_here > oct_api.txt
    echo.
    echo Please edit 'oct_api.txt' and add your real API key before continuing
    pause
)

echo.
echo Setup complete! Starting dashboard...
echo.
echo The dashboard will be available at: http://localhost:5000
echo Press Ctrl+C to stop the dashboard
echo.

REM Start the dashboard
python dashboard.py 