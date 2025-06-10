@echo off

REM Check if credentials are set
if "%OCTOPUS_API_KEY%"=="" (
    echo ❌ API credentials not found.
    echo Please run: setup_lifetime_credentials.bat first
    echo.
    pause
    exit /b 1
)

:start
echo ==================================================
echo   Octopus Energy Lifetime Data Fetcher
echo ==================================================
echo.
echo Choose an option:
echo.
echo 1. Fetch last 90 days
echo 2. Fetch last 365 days (1 year)
echo 3. Fetch last 730 days (2 years)
echo 4. Fetch all lifetime data (from 2020)
echo 5. Custom date range
echo 6. Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    echo.
    echo Fetching last 90 days...
    python octopus_lifetime_fetcher.py --days 90
    goto end
)

if "%choice%"=="2" (
    echo.
    echo Fetching last 365 days...
    python octopus_lifetime_fetcher.py --days 365
    goto end
)

if "%choice%"=="3" (
    echo.
    echo Fetching last 730 days...
    python octopus_lifetime_fetcher.py --days 730
    goto end
)

if "%choice%"=="4" (
    echo.
    echo Fetching all lifetime data (this may take a while)...
    python octopus_lifetime_fetcher.py --lifetime
    goto end
)

if "%choice%"=="5" (
    echo.
    set /p start_date="Enter start date (YYYY-MM-DD): "
    set /p end_date="Enter end date (YYYY-MM-DD): "
    echo.
    echo Fetching data from %start_date% to %end_date%...
    python octopus_lifetime_fetcher.py --start-date %start_date% --end-date %end_date%
    goto end
)

if "%choice%"=="6" (
    echo Goodbye!
    exit /b 0
)

echo Invalid choice. Please try again.
pause
goto start

:end
echo.
echo ==================================================
echo Data fetch complete! 
echo Your dashboard will now show the updated data.
echo Open http://127.0.0.1:8050 in your browser.
echo ==================================================
pause 