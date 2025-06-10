@echo off
echo ===================================================
echo    Octopus Energy API Credentials Setup
echo ===================================================
echo.
echo This will help you set up your API credentials for
echo fetching lifetime energy data.
echo.
echo You'll need:
echo 1. Your API Key (from Octopus Energy account dashboard)
echo 2. Your Account Number (format: A-AAAA1111)
echo.

:get_api_key
set /p api_key="Enter your Octopus API Key: "
if "%api_key%"=="" (
    echo API Key cannot be empty.
    goto get_api_key
)

:get_account
set /p account_number="Enter your Account Number (A-AAAA1111): "
if "%account_number%"=="" (
    echo Account Number cannot be empty.
    goto get_account
)

echo.
echo Setting environment variables...

REM Set environment variables for current session
set OCTOPUS_API_KEY=%api_key%
set OCTOPUS_ACCOUNT_NUMBER=%account_number%

echo ✅ Credentials set for current session.
echo.
echo Testing connection...

REM Test the connection
python octopus_lifetime_fetcher.py --days 1

if errorlevel 1 (
    echo ❌ Connection test failed. Please check your credentials.
    pause
    exit /b 1
)

echo.
echo ✅ Connection successful!
echo.
echo Your credentials are now set for this session.
echo To make them permanent, add these lines to your system environment variables:
echo.
echo   OCTOPUS_API_KEY=%api_key%
echo   OCTOPUS_ACCOUNT_NUMBER=%account_number%
echo.
echo Now you can:
echo 1. Run: fetch_lifetime_data.bat
echo 2. Or use: python octopus_lifetime_fetcher.py --lifetime
echo.

pause 