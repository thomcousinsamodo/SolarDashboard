# Octopus Tariff Tracker

A comprehensive tool for managing and tracking Octopus Energy tariff periods and rates over time.

## Features

- **Dual Timeline Management**: Separate timelines for import and export tariffs
- **Automatic Rate Fetching**: Fetches rates from Octopus Energy API including:
  - Standard rates for fixed/variable tariffs
  - Day/night rates for Economy 7 tariffs  
  - Half-hourly rates for Agile tariffs
- **Historical Rate Lookup**: Look up rates for any specific datetime
- **Timeline Validation**: Detect gaps and overlaps in tariff periods
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **CLI Interface**: Command-line tool for all operations
- **Configuration Persistence**: JSON-based configuration storage

## Quick Start

### 1. Installation

The tool requires Python 3.7+ and the following dependencies:
- `requests` for API calls
- `flask` for web interface (optional)

```bash
pip install requests flask
```

### 2. API Key Setup

Create an `oct_api.txt` file in the root directory with your Octopus Energy API key:
```
your_api_key_here
```

### 3. Basic Usage

```bash
# Run the example
python -m tariff_tracker.example

# Use the CLI
python -m tariff_tracker.web_interface --help

# Add a new tariff period
python -m tariff_tracker.web_interface add \
  --flow import \
  --start 2023-01-01 \
  --product AGILE-FLEX-22-11-25 \
  --name "Agile Octopus" \
  --type agile \
  --region C

# List all periods
python -m tariff_tracker.web_interface list

# Refresh all rates
python -m tariff_tracker.web_interface refresh
```

## Architecture

### Core Components

#### 1. Data Models (`models.py`)
- `TariffPeriod`: Represents a period when a specific tariff was active
- `TariffTimeline`: Collection of tariff periods for import or export
- `TariffConfig`: Complete configuration with both timelines
- `TariffRate`: Individual rate data with validity periods
- `StandingCharge`: Standing charge data

#### 2. API Client (`api_client.py`)
- Handles all communication with Octopus Energy API
- Automatic rate limiting and error handling
- Supports all tariff types (Fixed, Variable, Agile, Economy 7)
- Comprehensive request/response logging

#### 3. Timeline Manager (`timeline_manager.py`)
- High-level interface for managing tariff timelines
- Orchestrates API calls and data storage
- Provides rate lookup functionality
- Validates timeline integrity

#### 4. Logging System (`logging_config.py`)
- Structured logging with JSON format
- Separate log files for different components
- Performance monitoring and error tracking
- Configurable log levels

### Log Files

The system creates several log files in the `logs/` directory:

- `tariff_tracker.log` - Main application log
- `api_calls.log` - All API requests and responses
- `timeline_operations.log` - Timeline management operations
- `performance.log` - Performance metrics and timing
- `errors.log` - Error-only log for critical issues

## Configuration

### Tariff Types Supported

- **FIXED**: Fixed-rate tariffs with single unit rate
- **VARIABLE**: Variable tariffs that can change periodically  
- **AGILE**: Half-hourly pricing based on wholesale costs
- **ECONOMY7**: Time-of-use tariffs with day/night rates
- **GO**: Electric vehicle tariffs

### Region Codes

- A: Eastern England
- B: East Midlands  
- C: London (default)
- D: Merseyside and Northern Wales
- E: West Midlands
- F: North Eastern England
- G: North Western England
- H: Southern England
- J: South Eastern England
- K: South Western England
- L: Yorkshire
- M: Southern Wales
- N: South Scotland
- P: North Scotland

## API Reference

### TimelineManager

```python
from tariff_tracker.timeline_manager import TimelineManager

# Initialize
manager = TimelineManager("config.json")

# Add periods
period = manager.add_import_period(
    start_date=date(2023, 1, 1),
    end_date=None,  # Ongoing
    product_code="AGILE-FLEX-22-11-25",
    display_name="Agile Octopus",
    tariff_type=TariffType.AGILE,
    region="C"
)

# Fetch rates
manager.fetch_rates_for_period(period)

# Rate lookup
rate = manager.get_rate_at_datetime(
    datetime.now(), 
    FlowDirection.IMPORT
)

# Save configuration
manager.save_config()
```

### CLI Commands

```bash
# Add a period
python -m tariff_tracker.web_interface add \
  --flow import \
  --start 2023-01-01 \
  --end 2023-12-31 \
  --product VAR-22-11-01 \
  --name "Flexible Octopus" \
  --type variable \
  --region C \
  --notes "Previous tariff"

# List all periods
python -m tariff_tracker.web_interface list

# Show timeline status
python -m tariff_tracker.web_interface status

# Refresh rates for all periods
python -m tariff_tracker.web_interface refresh

# Look up rate for specific time
python -m tariff_tracker.web_interface rate \
  --datetime 2023-06-15T14:30:00 \
  --flow import \
  --type standard
```

## Logging and Debugging

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about operations
- `WARNING`: Warning messages about potential issues
- `ERROR`: Error messages for failed operations

### Setting Log Level

```bash
# Set log level for CLI
python -m tariff_tracker.web_interface --log-level DEBUG list

# Or in code
from tariff_tracker.logging_config import setup_logging
setup_logging("DEBUG")
```

### Log File Locations

All logs are stored in the `logs/` directory with automatic rotation:
- Max file size: 10MB (main log), 5MB (others)
- Backup files: 3-5 depending on log type
- Automatic compression of old files

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure `oct_api.txt` exists in the root directory
   - Check file permissions

2. **API Rate Limiting**
   - The system includes automatic delays between requests
   - Check `api_calls.log` for response codes

3. **Missing Rates**
   - Some historical periods may not have rates available
   - Check product codes are correct for the time period

4. **Timeline Validation Errors**
   - Use `python -m tariff_tracker.web_interface status` to check for gaps/overlaps
   - Review period start/end dates

### Debug Mode

Enable debug logging to see detailed information:

```bash
python -m tariff_tracker.web_interface --log-level DEBUG <command>
```

## Data Storage

### Configuration Format

The system stores configuration in JSON format:

```json
{
  "import_timeline": {
    "flow_direction": "import",
    "periods": [
      {
        "start_date": "2023-01-01",
        "end_date": null,
        "product_code": "AGILE-FLEX-22-11-25",
        "tariff_code": "E-1R-AGILE-FLEX-22-11-25-C",
        "display_name": "Agile Octopus",
        "tariff_type": "agile",
        "flow_direction": "import",
        "region": "C",
        "rates": [...],
        "standing_charges": [...],
        "notes": "",
        "last_updated": "2023-06-15T10:30:00"
      }
    ]
  },
  "export_timeline": {
    "flow_direction": "export", 
    "periods": [...]
  }
}
```

### Rate Data Structure

Each rate includes:
- `valid_from`: Start datetime (ISO format)
- `valid_to`: End datetime (ISO format) 
- `value_exc_vat`: Rate excluding VAT (pence/kWh)
- `value_inc_vat`: Rate including VAT (pence/kWh)
- `rate_type`: Type of rate (standard, day, night)

## Performance Considerations

- **API Calls**: The system respects API rate limits with automatic delays
- **Data Volume**: Agile tariffs generate ~17,500 rates per year per direction
- **Memory Usage**: Large datasets are processed in chunks
- **Storage**: JSON files can become large with historical data

## Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create API key file: `oct_api.txt`
4. Run example: `python -m tariff_tracker.example`

### Testing

The system includes comprehensive logging for testing and validation:
- All API calls are logged with timings
- Timeline operations include structured logging
- Performance metrics are captured automatically

## License

This project is released under the MIT License. 