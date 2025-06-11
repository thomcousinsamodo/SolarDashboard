# Octopus Energy Dashboard

A comprehensive web dashboard for monitoring solar energy consumption and managing electricity tariff periods using Octopus Energy data.

## Overview

This dashboard provides a unified interface to:
- **Monitor Solar Energy** - Visualize daily/hourly import and export data with interactive charts
- **Manage Tariff Periods** - Track different electricity tariffs over time with validation
- **Analyze Consumption** - Generate insights with rolling averages, net flow analysis, and consumption patterns
- **Rate Lookup** - Find historical rates for any date/time period

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Your Octopus Energy Credentials

You'll need:
- **API Key**: From your Octopus Energy account dashboard
- **Account Number**: Found on bills (format: A-AAAA1111)

Save your API key in `oct_api.txt`:
```
your_actual_api_key_here
```

### 3. Fetch Your Data (Optional)

If you want fresh consumption data:
```bash
python octopus_energy_fetcher.py
```

### 4. Run the Dashboard

```bash
python dashboard.py
```

The dashboard will be available at: **http://localhost:5000**

## Dashboard Features

### 🔌 Solar Energy Monitoring
- **Daily Overview Charts** - Import vs export with temperature overlay
- **Hourly Analysis** - Detailed consumption patterns throughout the day  
- **Net Flow Visualization** - Balance between consumption and generation
- **Energy Balance** - Cumulative totals and self-sufficiency metrics
- **Consumption Patterns** - Weekly/seasonal trend analysis

### ⚡ Tariff Management
- **Period Timeline** - Visual representation of tariff periods
- **Validation System** - Automatic detection of gaps and overlaps
- **Manual Entry** - Support for Economy 7 and custom tariffs
- **API Integration** - Automatic fetching of Octopus Energy rates
- **Export Support** - Dedicated handling for feed-in tariffs

### 📊 Advanced Features
- **Date Range Controls** - Quick presets (Last 30 days, Since Export, etc.)
- **Rolling Averages** - Smoothed trend lines for long-term analysis
- **Temperature Integration** - Weather data correlation (when available)
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Real-time Updates** - Live chart regeneration with new parameters

## File Structure

```
OctopusTracker/
├── dashboard.py              # Main dashboard application
├── templates/                # Web interface templates
├── tariff_tracker/          # Tariff management library
├── legacy_solar/            # Legacy standalone files
├── octopus_consumption_*.csv # Energy data files
├── tariff_config.json       # Tariff configuration
└── logs/                    # Application logs
```

## Data Sources

### Consumption Data
- `octopus_consumption_daily.csv` - Daily import/export totals
- `octopus_consumption_raw.csv` - Half-hourly meter readings

### Tariff Data
- API integration with Octopus Energy for live rates
- Manual entry support for historical/custom tariffs
- Validation and timeline management

## Dashboard Sections

### 🏠 Home Dashboard
- Quick statistics and validation status
- Recent activity and health checks
- Navigation to detailed sections

### ☀️ Solar Energy (`/solar`)
- Interactive charts with multiple visualization types
- Date range controls and filtering options
- Energy balance and efficiency metrics

### 🔋 Tariff Management (`/tariffs`)
- Timeline overview with validation results
- Period management interface
- Import/export tariff separation

### ➕ Add Periods (`/add-period`)
- Wizard-style tariff entry
- Economy 7 manual rate entry with VAT calculations
- API-driven tariff selection

### 📋 Periods List (`/periods`)
- Complete period overview with delete functionality
- Last updated timestamps and rate counts
- Bulk operations and management

### 🔍 Rate Lookup (`/rate-lookup`)
- Historical rate queries for any date/time
- Support for both import and export rates
- Detailed rate breakdown with validity periods

## Chart Types

### Daily Overview
- Line charts showing import vs export trends
- Optional temperature correlation
- Rolling averages for trend analysis

### Hourly Analysis  
- Heatmaps and time-series for detailed patterns
- Peak usage identification
- Seasonal variation analysis

### Net Flow
- Balance between import and export
- Self-sufficiency calculations
- Grid dependency metrics

### Energy Balance
- Cumulative totals over time
- Monthly/quarterly breakdowns
- Financial impact analysis

### Consumption Patterns
- Weekly day-of-week patterns
- Seasonal trend identification
- Usage categorization

## API Endpoints

### Dashboard APIs
- `/api/solar-chart` - Dynamic chart generation
- `/api/rate-lookup` - Historical rate queries
- `/api/available-tariffs` - Live tariff data from Octopus

### Management APIs
- `/api/delete-period` - Remove tariff periods
- `/refresh-rates` - Update tariff rates from API

## Configuration

### Environment Setup
Environment variables (optional):
```bash
export OCTOPUS_API_KEY="your_api_key"
export OCTOPUS_ACCOUNT_NUMBER="A-AAAA1111"
```

### Data Requirements
- Solar consumption data (CSV files)
- API key for tariff management
- Optional weather data integration

## Development

### Architecture
- **Flask backend** with Plotly for visualization
- **Bootstrap 5** responsive frontend
- **Library integration** - uses tariff_tracker as a module
- **Template system** with Jinja2 for dynamic content

### Key Components
- `dashboard.py` - Main application and routing
- `tariff_tracker/` - Tariff management library
- `templates/` - Web interface templates
- Chart generation functions for different visualization types

## Troubleshooting

### No Solar Data
- Ensure CSV files exist in root directory
- Check file format matches expected columns
- Verify date formatting and data types

### Tariff Issues
- Check API key in `oct_api.txt`
- Verify internet connection for API calls
- Review logs for specific error messages

### Chart Loading
- Enable browser developer tools for detailed errors
- Check console for JavaScript issues
- Verify chart data format and structure

## Migration from Legacy

If upgrading from the standalone solar dashboard:
- Legacy files moved to `legacy_solar/` directory  
- All functionality integrated into main dashboard
- Configuration and data files remain in same location
- No data migration required

## License

This project is provided as-is for educational and personal use with Octopus Energy data. 