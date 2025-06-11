# 📊 Octopus Energy Dashboard - Repository Summary

## 🎯 **Primary Purpose**

This repository provides a **comprehensive web dashboard** for Octopus Energy customers to monitor solar energy consumption and manage electricity tariff periods.

## 🚀 **Quick Start**

```bash
# Install dependencies
pip install -r requirements.txt

# Start the dashboard
python dashboard.py

# Access at: http://localhost:5000
```

## 📁 **Repository Structure**

### Core Application
- `dashboard.py` - **Main dashboard application**
- `templates/` - Web interface templates
- `tariff_tracker/` - Tariff management library (imported)

### Data Files
- `octopus_consumption_*.csv` - Energy consumption data
- `tariff_config.json` - Tariff period configuration
- `oct_api.txt` - Octopus Energy API key

### Utilities & Setup
- `octopus_energy_fetcher.py` - Data fetching utility
- `setup_and_run.bat` - Automated setup script
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - Main documentation and setup guide
- `MIGRATION_NOTICE.md` - Repository restructure information
- `LIFETIME_DATA_GUIDE.md` - Historical data fetching guide

### Legacy & Reference
- `legacy_solar/` - Previous standalone solar dashboard
- `bills/` - Historical bill data
- `logs/` - Application logs

## 🔧 **Dashboard Features**

### Solar Energy Monitoring
- **Interactive Charts** - Daily overview, hourly analysis, net flow
- **Energy Balance** - Import/export totals and self-sufficiency
- **Pattern Analysis** - Consumption trends and seasonal variations
- **Date Controls** - Flexible range selection with quick presets

### Tariff Management  
- **Period Timeline** - Visual tariff period representation
- **Validation System** - Gap and overlap detection
- **Manual Entry** - Economy 7 and custom tariff support
- **API Integration** - Live Octopus Energy rate fetching

### Advanced Capabilities
- **Rate Lookup** - Historical rate queries for any date/time
- **Rolling Averages** - Trend smoothing for long-term analysis
- **Temperature Integration** - Weather correlation (when available)
- **Responsive Design** - Mobile, tablet, and desktop support

## 📊 **Data Integration**

### Input Sources
- **CSV Files** - Daily and half-hourly consumption data
- **Octopus API** - Live tariff rates and product information
- **Manual Entry** - Custom tariffs and historical rates

### Output Capabilities
- **Interactive Visualizations** - Plotly charts with real-time updates
- **Export Support** - Data analysis for feed-in tariffs
- **Configuration Management** - Persistent tariff period storage

## 🔄 **Architecture**

### Backend
- **Flask** - Web framework with RESTful API endpoints
- **Pandas** - Data processing and analysis
- **Plotly** - Interactive chart generation

### Frontend  
- **Bootstrap 5** - Responsive UI framework
- **Jinja2** - Template engine for dynamic content
- **Vanilla JS** - Chart interactions and AJAX calls

### Integration
- **Library Approach** - Uses tariff_tracker as imported module
- **No Code Duplication** - Leverages existing functionality
- **Modular Design** - Clear separation of concerns

## 🎯 **Target Users**

### Primary Audience
- **Octopus Energy customers** with solar panels or battery storage
- **Energy enthusiasts** interested in consumption pattern analysis
- **Tariff switchers** who need to track rate changes over time

### Use Cases
- **Daily Monitoring** - Track energy import/export patterns
- **Financial Analysis** - Calculate tariff costs and savings
- **Solar Optimization** - Analyze generation vs consumption
- **Historical Research** - Look up rates for any period

## 🔮 **Future Potential**

The dashboard provides a solid foundation for additional features:
- **Bill Integration** - Automatic cost calculations
- **Forecasting** - Predictive analytics for usage patterns
- **Automation** - Smart tariff switching recommendations
- **Extended APIs** - Additional energy supplier integration

## 📈 **Development Status**

- ✅ **Stable Core** - Dashboard fully functional with comprehensive features
- ✅ **Data Integration** - Solar monitoring and tariff management working
- ✅ **User Interface** - Responsive design with intuitive navigation
- ✅ **Documentation** - Complete setup guides and feature documentation

## 🎉 **Ready for Production Use**

The dashboard is production-ready for personal use with:
- Comprehensive error handling and logging
- Responsive design for all device types
- Full feature parity with legacy applications
- Clear migration path from previous versions 