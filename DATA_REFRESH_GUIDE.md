# 📡 Data Refresh Guide

The Unified Octopus Energy Dashboard now includes automatic data refresh functionality to keep your consumption and pricing data up-to-date directly from the Octopus Energy API.

## 🚀 Quick Setup

### 1. Set Up API Credentials

Run the credential setup script:
```bash
python setup_credentials.py
```

This will prompt you for:
- **API Key**: Get yours from [Octopus Energy Developer Dashboard](https://octopus.energy/dashboard/developer/)
- **Account Number**: Found in your Octopus Energy account (format: A-AAAA1111)

### 2. Use the Data Refresh Center

1. Open the main dashboard at `http://127.0.0.1:8050`
2. Find the **Data Refresh Center** section at the top
3. Choose your refresh option:
   - **Consumption Data**: Update solar generation and energy usage
   - **Pricing Data**: Update tariff rates and pricing information  
   - **Complete Refresh**: Update both (recommended for daily use)

## 📊 What Gets Updated

### Consumption Data Refresh
- ✅ **Solar generation data** (export readings)
- ✅ **Energy consumption data** (import readings)  
- ✅ **Half-hourly interval data** for accurate charts
- ✅ **Daily summary statistics**
- 📁 **Files updated**: `octopus_consumption_raw.csv`, `octopus_consumption_daily.csv`

### Pricing Data Refresh
- ✅ **Import tariff rates** (all configured periods)
- ✅ **Export tariff rates** (solar feed-in rates)
- ✅ **Standing charges** 
- ✅ **Agile pricing** (if using Agile tariffs)
- 📁 **Files updated**: `pricing_raw.csv`, tariff database

## ⚙️ Configuration Options

### Consumption Data Period
Choose how much historical data to fetch:
- **Last 7 days**: Quick update (2-3 minutes)
- **Last 30 days**: Standard refresh (5-10 minutes)  
- **Last 90 days**: Quarterly update (10-15 minutes)
- **Last year**: Annual refresh (20-30 minutes)

### Automatic vs Manual
- **Manual**: Use the Data Refresh Center buttons
- **Automatic**: Set up scheduled refreshes (see Advanced Setup below)

## 🔧 Advanced Setup

### Environment Variables (Alternative to files)
```bash
export OCTOPUS_API_KEY="your_api_key_here"
export OCTOPUS_ACCOUNT_NUMBER="A-AAAA1111"
```

### Scheduled Refresh (Windows Task Scheduler)
Create a batch file `daily_refresh.bat`:
```batch
@echo off
cd /d "C:\path\to\OctopusTracker"
python -c "
import requests
response = requests.post('http://127.0.0.1:8050/api/refresh-data', 
                        json={'type': 'all', 'days': 30})
print('Refresh result:', response.json())
"
```

### Scheduled Refresh (Linux/Mac Cron)
Add to crontab (`crontab -e`):
```bash
# Refresh data daily at 8 AM
0 8 * * * cd /path/to/OctopusTracker && python -c "import requests; requests.post('http://127.0.0.1:8050/api/refresh-data', json={'type': 'all', 'days': 30})"
```

## 📈 Dashboard Integration

After refresh, your dashboard will automatically show:
- 🔄 **Updated charts** with latest consumption data
- 💰 **Current pricing** for rate lookups and timeline charts
- 📊 **Refreshed summary statistics** 
- 🏠 **Real-time energy balance** calculations

## 🛠️ Troubleshooting

### Common Issues

#### ❌ "API credentials not found"
**Solution**: Run `python setup_credentials.py` or check environment variables

#### ❌ "No consumption data fetcher script found"
**Solution**: Ensure `octopus_lifetime_fetcher.py` exists in the project directory

#### ❌ "Tariff tracker not available"
**Solution**: Check if tariff configuration files exist and are properly set up

#### ⚠️ "Partial Success" warnings
**Possible causes**:
- Internet connection issues during fetch
- API rate limiting (retry after a few minutes)
- Some tariff periods missing configuration

#### 🐌 "Data fetch timed out"
**Solution**: 
- Reduce the number of days to fetch
- Check internet connection stability
- For large datasets, use the standalone fetcher scripts

### Manual Fallback

If the integrated refresh fails, use the standalone scripts:

```bash
# For consumption data
python octopus_lifetime_fetcher.py --days 30

# For pricing data (if tariff tracker available)
python generate_pricing_data.py
```

## 🔒 Security & Privacy

### Data Protection
- ✅ API credentials stored locally only
- ✅ No data sent to third parties
- ✅ All processing happens on your machine
- ✅ Personal energy data stays private

### File Security
- 🔐 `oct_api.txt` and `account_info.txt` contain sensitive data
- 🚫 Automatically excluded from version control (.gitignore)
- 💡 **Tip**: Set restrictive file permissions on credential files

## 📋 API Rate Limits

The Octopus Energy API is generally permissive, but to be respectful:
- ⏱️ Built-in delays between requests
- 🔄 Automatic retry on temporary failures
- 📊 Efficient pagination for large datasets
- 🎯 Targeted date ranges to minimize requests

## 🎯 Best Practices

### Daily Routine
1. **Morning**: Refresh last 7 days for overnight data
2. **Weekly**: Refresh last 30 days for complete weekly patterns
3. **Monthly**: Refresh last 90 days for seasonal analysis

### Data Quality
- ✅ **Verify dates**: Check that refresh covers desired time periods
- ✅ **Monitor logs**: Watch for any API errors or warnings
- ✅ **Compare totals**: Ensure data consistency after refresh

### Dashboard Usage
- 🔄 **Auto-reload**: Dashboard refreshes automatically after successful data update
- 📊 **Chart updates**: All solar charts immediately reflect new data
- 💰 **Pricing current**: Rate lookups use freshest tariff information

## 🆘 Support

### Getting Help
1. **Check logs**: Dashboard shows detailed refresh status
2. **Manual scripts**: Try standalone fetchers for debugging
3. **Verify credentials**: Re-run setup if authentication fails
4. **API status**: Check [Octopus Energy Status](https://status.octopus.energy/) for outages

### Feature Requests
The data refresh system is designed to be extensible. Future enhancements could include:
- 📅 Scheduled automatic refreshes
- 📱 Mobile notifications on completion
- 🔔 Email alerts for refresh failures
- 📈 Data quality monitoring and validation

---

**🐙 Happy energy tracking with your Octopus Energy Dashboard!** 