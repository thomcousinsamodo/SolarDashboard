@echo off
echo ===================================================
echo    Get ALL Your Octopus Energy History!
echo ===================================================
echo.

REM Check if credentials are already set
if not "%OCTOPUS_API_KEY%"=="" if not "%OCTOPUS_ACCOUNT_NUMBER%"=="" (
    echo [OK] Credentials found! Proceeding with data fetch...
    goto fetch_data
)

echo This will fetch ALL your historical energy data.
echo Perfect for seeing long-term solar generation patterns!
echo.
echo First, I need your Octopus Energy credentials:
echo.

:get_credentials
set /p api_key="Enter your API Key: "
if "%api_key%"=="" (
    echo Please enter your API key.
    goto get_credentials
)

set /p account_number="Enter your Account Number (A-AAAA1111): "
if "%account_number%"=="" (
    echo Please enter your account number.
    goto get_credentials
)

REM Set credentials
set OCTOPUS_API_KEY=%api_key%
set OCTOPUS_ACCOUNT_NUMBER=%account_number%

:fetch_data
echo.
echo [STARTING] Fetching ALL your historical energy data...
echo [INFO] This may take 15-30 minutes depending on how long you've had your smart meter.
echo [INFO] You'll get detailed solar generation and consumption patterns!
echo.

python octopus_lifetime_fetcher.py --lifetime

if errorlevel 1 (
    echo.
    echo [ERROR] Something went wrong. Please check your credentials and try again.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Your lifetime data has been downloaded!
echo.
echo [DASHBOARD] Your dashboard now has ALL your historical data!
echo             Open: http://127.0.0.1:8050
echo.
echo [FEATURES] You can now see:
echo            * Long-term solar generation trends
echo            * Seasonal energy patterns  
echo            * Year-over-year comparisons
echo            * Complete consumption history
echo.
echo [TIP] Use the date picker in the dashboard to explore different time periods!
echo.

pause 