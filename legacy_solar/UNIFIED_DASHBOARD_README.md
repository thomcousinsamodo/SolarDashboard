# 🐙 Unified Octopus Energy Dashboard

A comprehensive web dashboard that combines solar energy tracking and electricity tariff management into a single, unified interface.

## 🌟 Features

### Solar Energy Tracking
- **Daily & Hourly Analysis**: Visualize your energy consumption and solar generation patterns
- **Interactive Charts**: Multiple chart types including daily overview, net flow, energy balance, and consumption patterns
- **Weather Integration**: Correlate solar generation with weather data (optional)
- **Key Metrics**: Track total import/export, net consumption, and self-sufficiency rates
- **Date Range Filtering**: Analyze specific time periods with flexible date controls

### Tariff Management
- **Period Management**: Add, view, and manage electricity tariff periods for both import and export
- **Rate Lookup**: Find exact electricity rates for specific dates and times
- **Timeline Validation**: Automatically detect gaps and overlaps in your tariff configuration
- **API Integration**: Fetches real-time rates from Octopus Energy API
- **Multiple Tariff Types**: Support for Agile, Go, Fixed, and Variable tariffs

## 🚀 Getting Started

### Prerequisites
```bash
pip install flask plotly pandas numpy
```

### Required Data Files
For solar tracking functionality, ensure these files are present in the project root:
- `octopus_consumption_daily.csv` - Daily consumption/generation data
- `octopus_consumption_raw.csv` - Hourly interval data

### Running the Dashboard
```bash
python unified_dashboard.py
```

The dashboard will be available at: **http://localhost:5000**

## 📊 Dashboard Sections

### 1. Main Dashboard (`/`)
- **System Status**: Overview of available features
- **Solar Energy Summary**: Key metrics and totals
- **Tariff Management Summary**: Active periods and validation status
- **Quick Actions**: Direct links to all major features

### 2. Solar Energy Dashboard (`/solar`)
- **Interactive Charts**: 5 different chart types
- **Chart Controls**: Date range, chart type, and display options
- **Quick Statistics**: Daily averages and insights
- **Temperature Overlay**: Weather correlation (if available)

**Available Chart Types:**
- **Daily Overview**: Daily import/export with optional temperature overlay
- **Hourly Analysis**: Detailed hourly consumption patterns
- **Net Energy Flow**: Shows net consumption (import - export)
- **Energy Balance**: Pie chart showing import/export proportions
- **Consumption Pattern**: Trend analysis with rolling averages

### 3. Tariff Management (`/tariffs`)
- **Period Overview**: Current import/export periods
- **Timeline Validation**: Status of your tariff configuration
- **Quick Actions**: Add periods, lookup rates, refresh data

### 4. Rate Lookup (`/rate-lookup`)
- **Date/Time Lookup**: Find exact rates for specific moments
- **Import/Export Rates**: Support for both flow directions
- **Rate Details**: Shows VAT-inclusive/exclusive rates and validity periods

## 🎛️ Features & Controls

### Solar Chart Options
- **Show Temperature**: Overlay weather data on energy charts
- **Use Rolling Average**: Smooth out daily variations with rolling averages
- **Date Range Selection**: Focus on specific time periods
- **Quick Range Buttons**: Last 30 days, 90 days, or all data

### Tariff Management
- **Flow Direction**: Separate handling of import vs export tariffs
- **Tariff Types**: Agile, Go, Fixed, Variable
- **Regional Support**: All UK electricity regions (A-P)
- **Automatic Rate Fetching**: Pulls latest rates from Octopus Energy API

## 📈 Understanding Your Data

### Solar Metrics Explained
- **Total Grid Import**: Energy consumed from the grid (kWh)
- **Total Solar Export**: Energy generated and fed back to grid (kWh)
- **Net Consumption**: Import minus Export (positive = net consumer, negative = net generator)
- **Self Sufficiency**: Percentage of consumption met by your own generation

### Energy Flow Indicators
- 🔴 **Red/Above Zero**: Net energy consumption (importing more than exporting)
- 🟢 **Green/Below Zero**: Net energy generation (exporting more than importing)

## 🔧 Configuration

### Optional Components
The dashboard gracefully handles missing components:

- **Weather Integration**: If `weather_integration.py` is not available, temperature overlays are disabled
- **Tariff Tracker**: If tariff tracker modules are not available, only solar features are shown
- **Data Files**: Missing CSV files show appropriate warnings with guidance

### Customization
The dashboard uses a responsive Bootstrap design and can be customized by:
- Modifying the color scheme in `unified_dashboard.py`
- Updating templates in the `templates/` directory
- Adding new chart types by extending the chart creation functions

## 🚨 Troubleshooting

### Common Issues

**Dashboard won't start:**
- Check that Flask is installed: `pip install flask`
- Ensure port 5000 is not in use by another application

**No solar data showing:**
- Verify `octopus_consumption_daily.csv` exists in the project root
- Check the CSV file has the required columns: `date`, `meter_type`, `total_kwh`

**Tariff features missing:**
- Ensure the `tariff_tracker` module is properly installed
- Check that `tariff_config.json` exists and is readable

**Charts not loading:**
- Verify Plotly is installed: `pip install plotly`
- Check browser console for JavaScript errors

### Performance Tips
- For large datasets (>1 year), use date range filtering to improve chart rendering speed
- The dashboard automatically adjusts rolling average windows based on data range
- Browser caching improves load times for repeated visits

## 🔗 Integration

### Standalone Usage
The unified dashboard can be used independently or alongside:
- The original `solar_dashboard.py` (Dash-based)
- The original `tariff_tracker.web_dashboard` (Flask-based)

### API Endpoints
- `POST /api/solar-chart`: Generate solar energy charts
- `POST /api/rate-lookup`: Look up electricity rates
- `POST /add-period`: Add new tariff periods

## 📝 Data Sources

### Solar Data
Expected CSV format for solar data files:
```csv
date,meter_type,total_kwh
2024-01-01,import,15.2
2024-01-01,export,8.7
```

### Tariff Data
Tariff information is fetched from:
- Octopus Energy API (live rates)
- Local configuration file (`tariff_config.json`)

## 🎯 Future Enhancements

Potential improvements for future versions:
- **Cost Calculations**: Combine tariff rates with consumption data for bill estimates
- **Export Forecasting**: Predict solar generation based on weather forecasts
- **Historical Comparisons**: Year-over-year consumption analysis
- **Mobile App**: Native mobile interface for key metrics
- **Data Export**: CSV/Excel export of charts and calculations

---

## 🛠️ Technical Details

**Built with:**
- **Backend**: Flask (Python web framework)
- **Frontend**: Bootstrap 5 + Plotly.js
- **Charts**: Plotly (interactive JavaScript charts)
- **Data Processing**: Pandas + NumPy

**Browser Compatibility:**
- Chrome, Firefox, Safari, Edge (modern versions)
- Responsive design works on desktop, tablet, and mobile

---

*For technical support or feature requests, please refer to the project documentation or create an issue in the project repository.* 