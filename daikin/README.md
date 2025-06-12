# Daikin Heat Pump Integration

Simple two-script solution for connecting to Daikin heat pumps via the Onecta Cloud API with database storage and comprehensive logging.

## Quick Start

### 1. Authentication
```bash
# Start authentication process
python daikin_auth.py

# Follow the prompts:
# 1. Open the provided URL in your browser
# 2. Log in to your Daikin account  
# 3. Copy the 'code=' parameter from the error page URL
# 4. Run: python daikin_auth.py --code YOUR_CODE_HERE
```

### 2. Get Heat Pump Data
```bash
# Simple summary
python daikin_api.py

# Full data
python daikin_api.py --full

# List devices
python daikin_api.py --devices

# JSON output
python daikin_api.py --json
```

### 3. Control Heat Pump
```bash
# Turn on/off
python daikin_api.py --turn-on
python daikin_api.py --turn-off

# Set temperatures
python daikin_api.py --set-temp 21        # Room temperature
python daikin_api.py --set-hot-water 48   # Hot water temperature

# Hot water controls
python daikin_api.py --hot-water-on      # Turn hot water on
python daikin_api.py --hot-water-off     # Turn hot water off
```

### 4. Database Storage
```bash
# Save current data to database
python daikin_api.py --save-to-db

# Update database with latest data
python daikin_api.py --update-db

# View database statistics
python daikin_database.py --stats

# View consumption summary
python daikin_database.py --summary 7    # Last 7 days
```

## Files

- **`daikin_auth.py`** - Handle OAuth authentication 
- **`daikin_api.py`** - Get heat pump data and control device
- **`daikin_database.py`** - Database storage and management
- **`tokens.json`** - Stored access tokens (auto-generated)

## Database Integration

The Daikin integration now stores data in the same database as your Octopus Energy dashboard (`../data/energy_data.db`):

### Tables Created
- **`daikin_consumption`** - Historical consumption data (daily, weekly, monthly)
- **`daikin_status`** - Temperature readings and device status snapshots

### Data Stored
- **Consumption**: Electrical usage for climate control and hot water heating
- **Temperatures**: Room, outdoor, leaving water, and tank temperatures  
- **Status**: On/off states, target temperatures, error conditions
- **Time Series**: Regular snapshots for historical analysis

### Usage Examples
```bash
# Create database tables
python daikin_database.py --create-tables

# Update with fresh data
python daikin_database.py --update

# Show data statistics
python daikin_database.py --stats

# Consumption summary for last 30 days
python daikin_database.py --summary 30
```

## Comprehensive Logging

The Daikin integration is fully integrated with your dashboard's comprehensive logging system:

### Log Files Generated
- **`logs/tariff_tracker.log`** - All Daikin operations with detailed context
- **`logs/performance.log`** - API call timing and performance metrics
- **`logs/api_calls.log`** - Structured API call logs (when main dashboard is running)
- **`logs/errors.log`** - Error-only logs for critical issues

### What Gets Logged
- **🌐 API Calls**: Method, URL, parameters, response times, status codes
- **⚡ Performance**: Operation timing and duration metrics
- **🎯 Control Commands**: Temperature changes, on/off operations
- **💾 Database Operations**: Data save operations and record counts
- **🚨 Errors**: Failed API calls, authentication issues, database errors

### Structured Logging Format
All logs use JSON format for easy parsing:
```json
{
  "type": "api_call",
  "method": "PATCH", 
  "url": "https://api.onecta.daikineurope.com/v1/gateway-devices/.../characteristics/temperatureControl",
  "params": {
    "characteristic": "temperatureControl",
    "value": 21.5,
    "path": "/operationModes/heating/setpoints/roomTemperature"
  },
  "response_status": 204,
  "response_time_ms": 111.624,
  "timestamp": "2025-06-12T15:45:22.257650"
}
```

### Performance Tracking
Monitor heat pump operation performance:
- **API response times** (typically 100-400ms)
- **Database save duration** (typically 10-50ms)
- **Total operation time** for complete updates

### Log Rotation
- **Automatic rotation** at midnight
- **File size limits** (10MB per file)
- **Backup retention** (5 backup files)
- **UTF-8 encoding** for international characters

## Usage in Your Code

```python
from daikin_api import DaikinAPI
from daikin_database import update_daikin_database, get_latest_daikin_status

# Initialize API
api = DaikinAPI()

# Get simple summary
summary = api.get_simple_summary()
print(f"Heat pump is {summary['status']} at {summary['temperatures']}")

# Get full data
data = api.get_heat_pump_data()
print(f"Device: {data['device_name']}")
print(f"Sensors: {data['sensors']}")

# Control heat pump
api.turn_on()                           # Turn on
api.turn_off()                          # Turn off
api.set_room_temperature(21.5)          # Set room temp
api.set_hot_water_temperature(48)       # Set hot water temp
api.turn_hot_water_on()               # Turn hot water on
api.turn_hot_water_off()              # Turn hot water off

# Database operations
result = update_daikin_database()       # Save latest data
latest = get_latest_daikin_status()     # Get latest status
```

## Authentication Commands

```bash
# Check if authenticated
python daikin_auth.py --status

# Refresh tokens
python daikin_auth.py --refresh
```

## API Commands

```bash
# Basic usage
python daikin_api.py                    # Simple summary
python daikin_api.py --summary           # Simple summary  
python daikin_api.py --full              # Full heat pump data
python daikin_api.py --devices           # List all devices
python daikin_api.py --sites             # List all sites
python daikin_api.py --json              # Raw JSON output

# Database commands
python daikin_api.py --save-to-db        # Save current data
python daikin_api.py --update-db         # Update database
```

## Data Analysis

The consumption data covers:
- **Daily data**: Last 24 days (array positions 0-23)
- **Weekly data**: Last 14 weeks (limited historical data)
- **Monthly data**: Last 24 months (limited historical data)

Separate tracking for:
- **Climate Control**: Room heating system
- **Hot Water Tank**: Domestic hot water heating

Perfect complement to your existing Octopus Energy dashboard data! 