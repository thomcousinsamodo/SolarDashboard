# Octopus Energy API Data Fetcher

A Python script to fetch and analyze electricity import and export data from the Octopus Energy API.

## Features

- Fetch account information and meter details
- Download import and export electricity consumption data
- Analyze consumption patterns with daily and monthly summaries
- Export data to CSV files for further analysis
- Handle pagination for large datasets
- Proper error handling and authentication

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install requests pandas python-dateutil
```

### 2. Get Your API Credentials

You'll need:
- **API Key**: Get this from your Octopus Energy account dashboard
- **Account Number**: Found on your bills or account dashboard (format: A-AAAA1111)

To get your API key:
1. Log into your Octopus Energy account
2. Go to your account dashboard
3. Look for "Developer" or "API" settings
4. Generate or copy your API key

### 3. Set Environment Variables (Recommended)

```bash
export OCTOPUS_API_KEY="your_actual_api_key_here"
export OCTOPUS_ACCOUNT_NUMBER="A-AAAA1111"
```

On Windows (PowerShell):
```powershell
$env:OCTOPUS_API_KEY="your_actual_api_key_here"
$env:OCTOPUS_ACCOUNT_NUMBER="A-AAAA1111"
```

## Usage

### Test Public API (No Authentication Required)

Start by testing the public endpoints:

```bash
python octopus_api_example.py
```

This will:
- Fetch available Octopus Energy products
- Show sample Agile tariff prices
- Display product details and regional pricing

### Fetch Your Consumption Data

Once you have your credentials set up:

```bash
python octopus_energy_fetcher.py
```

This will:
- Fetch your account information and meter details
- Download the last 30 days of consumption data
- Generate daily and monthly summaries
- Save data to CSV files

### Output Files

The script generates these CSV files:
- `octopus_consumption_raw.csv` - All half-hourly readings
- `octopus_consumption_daily.csv` - Daily consumption summaries
- `octopus_consumption_monthly.csv` - Monthly consumption summaries

## Understanding the Data

### Import vs Export Meters

- **Import**: Electricity you consume from the grid
- **Export**: Electricity you send back to the grid (e.g., from solar panels)

### Data Format

Each reading includes:
- `interval_start`: When the measurement period started
- `interval_end`: When the measurement period ended
- `consumption`: Energy consumed/exported in kWh
- `meter_type`: "import" or "export"

### Time Zones

- The API returns data in UTC in winter, local time in summer
- The script automatically handles timezone conversion to UK local time for analysis

## API Endpoints Used

### Authentication Required
- `/v1/accounts/{account_number}/` - Account and meter information
- `/v1/electricity-meter-points/{mpan}/meters/{serial}/consumption/` - Consumption data

### Public (No Authentication)
- `/v1/products/` - Available tariffs and products
- `/v1/products/{product_code}/` - Specific product details
- `/v1/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/` - Pricing data

## Customization

### Change Date Range

Edit the main() function in `octopus_energy_fetcher.py`:

```python
# Change from 30 days to 90 days
start_date = end_date - timedelta(days=90)
```

### Add Your Own Analysis

The `DataAnalyzer` class can be extended with additional methods:

```python
class DataAnalyzer:
    @staticmethod
    def peak_usage_analysis(df: pd.DataFrame) -> pd.DataFrame:
        # Your custom analysis here
        pass
```

## Rate Limiting

The Octopus Energy API doesn't have strict rate limits, but be considerate:
- Don't make excessive requests
- Cache data when possible
- Use appropriate page sizes for large datasets

## Troubleshooting

### Authentication Errors
- Double-check your API key and account number
- Ensure environment variables are set correctly
- Try the public API test first

### Missing Data
- Consumption data may not be immediately available
- SMETS1 meters: Usually available by 9am the next day
- SMETS2 meters: May take longer to appear

### Time Zone Issues
- Always use UTC format for API requests
- The script handles timezone conversion automatically

## API Documentation

For more details about the Octopus Energy API:
- [Official API Documentation](https://developer.octopus.energy/rest/guides/endpoints)
- [Unofficial API Guide](https://www.guylipman.com/octopus/api_guide.html)

## License

This project is provided as-is for educational and personal use. 