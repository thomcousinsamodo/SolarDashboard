# 🌟 Octopus Energy Lifetime Data Fetcher

This enhanced tool allows you to fetch **all your historical energy data** from Octopus Energy, not just the last 30 days!

## 🚀 Quick Start

### Option 1: Use the Easy Batch File (Windows)
```bash
./fetch_lifetime_data.bat
```
This gives you a menu with common options:
1. Last 90 days
2. Last 365 days (1 year)  
3. Last 730 days (2 years)
4. **All lifetime data** (from 2020)
5. Custom date range

### Option 2: Command Line Usage

```bash
# Fetch all available data (lifetime)
python octopus_lifetime_fetcher.py --lifetime

# Fetch last year
python octopus_lifetime_fetcher.py --days 365

# Custom date range
python octopus_lifetime_fetcher.py --start-date 2023-01-01 --end-date 2024-12-31

# Fetch last 6 months
python octopus_lifetime_fetcher.py --days 180
```

## 📊 What You Get

The enhanced fetcher provides:

### **📈 Multiple Summary Levels:**
- **Daily summaries** - Perfect for the dashboard
- **Monthly summaries** - Great for long-term trends
- **Yearly summaries** - Annual consumption patterns

### **🔍 Enhanced Analytics:**
- Total consumption and generation over any period
- Average daily/monthly/yearly values
- Complete date range coverage
- Progress tracking during large downloads

### **💾 Smart Data Management:**
- Automatically updates dashboard files
- Creates timestamped backups
- Handles large datasets efficiently
- Rate limiting to be API-friendly

## ⚙️ Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--lifetime` | Fetch all available data from 2020 | `--lifetime` |
| `--days N` | Fetch last N days | `--days 365` |
| `--start-date` | Start date (YYYY-MM-DD) | `--start-date 2023-01-01` |
| `--end-date` | End date (YYYY-MM-DD) | `--end-date 2024-12-31` |
| `--chunk-days` | Days per API request (default 90) | `--chunk-days 60` |
| `--delay` | Delay between requests (default 0.5s) | `--delay 1.0` |

## 🎯 Usage Examples

### **Scenario 1: Solar Panel Owner**
Get all data since you installed solar panels:
```bash
python octopus_lifetime_fetcher.py --start-date 2023-06-15
```

### **Scenario 2: New Customer**
Get the last 2 years to see seasonal patterns:
```bash
python octopus_lifetime_fetcher.py --days 730
```

### **Scenario 3: Data Analysis**
Get specific period for analysis:
```bash
python octopus_lifetime_fetcher.py --start-date 2023-01-01 --end-date 2023-12-31
```

### **Scenario 4: Everything!**
Get all your historical data:
```bash
python octopus_lifetime_fetcher.py --lifetime
```

## 🌐 Dashboard Integration

After fetching new data:

1. **Automatic Update**: The dashboard files are automatically updated
2. **Refresh Browser**: Go to http://127.0.0.1:8050 and refresh
3. **New Date Range**: The dashboard will show your extended date range
4. **Enhanced Analytics**: More data = better trend analysis!

## ⏱️ Performance & Rate Limiting

### **Chunking Strategy:**
- Data is fetched in chunks (default: 90 days per request)
- Progress is displayed during large downloads
- Automatic rate limiting between requests

### **Time Estimates:**
- **90 days**: ~1-2 minutes
- **365 days**: ~5-8 minutes  
- **2+ years**: ~10-20 minutes
- **Lifetime**: ~15-30 minutes (depends on when your smart meter was installed)

### **Data Volumes:**
- Each day = ~48 readings (30-minute intervals)
- 1 year ≈ 17,500 readings
- 2 years ≈ 35,000 readings

## 🔧 Advanced Configuration

### **Adjust Chunk Size:**
For slower connections or API limits:
```bash
python octopus_lifetime_fetcher.py --lifetime --chunk-days 30 --delay 1.0
```

### **Custom Rate Limiting:**
Be extra gentle with the API:
```bash
python octopus_lifetime_fetcher.py --days 365 --delay 2.0
```

## 📁 Output Files

The tool creates several files:

### **Dashboard Files (Updated):**
- `octopus_consumption_raw.csv` - All readings (dashboard compatible)
- `octopus_consumption_daily.csv` - Daily summaries (dashboard compatible)
- `octopus_consumption_monthly.csv` - Monthly summaries

### **Timestamped Backups:**
- `octopus_consumption_raw_YYYYMMDD_HHMMSS.csv`
- `octopus_consumption_daily_YYYYMMDD_HHMMSS.csv`
- `octopus_consumption_monthly_YYYYMMDD_HHMMSS.csv`

## 🚨 Important Notes

### **API Credentials:**
Make sure your environment variables are set:
```bash
export OCTOPUS_API_KEY="your_actual_api_key"
export OCTOPUS_ACCOUNT_NUMBER="A-AAAA1111"
```

### **Data Availability:**
- Smart meter data typically available from installation date
- SMETS1 meters: Data available next day
- SMETS2 meters: Usually available within a few hours
- Historical data: Available back to meter installation

### **Rate Limiting:**
- The tool includes automatic delays between requests
- Octopus Energy API is generally generous with rate limits
- Large downloads (lifetime data) may take 15-30 minutes

## 🎉 Dashboard Benefits

With lifetime data, your dashboard becomes much more powerful:

### **🔍 Long-term Trends:**
- Seasonal patterns in solar generation
- Year-over-year consumption changes
- Long-term efficiency improvements

### **📊 Better Analytics:**
- More accurate trend lines
- Seasonal pattern recognition
- Historical performance comparisons

### **📅 Flexible Analysis:**
- Filter by any date range in your history
- Compare different periods
- Track long-term changes

## 🆘 Troubleshooting

### **Large Downloads Timing Out:**
```bash
# Reduce chunk size and add delay
python octopus_lifetime_fetcher.py --lifetime --chunk-days 30 --delay 1.0
```

### **API Rate Limit Errors:**
```bash
# Increase delay between requests
python octopus_lifetime_fetcher.py --days 365 --delay 2.0
```

### **Memory Issues with Large Datasets:**
The tool is optimized for large datasets, but if you have issues:
```bash
# Fetch smaller chunks and combine later
python octopus_lifetime_fetcher.py --start-date 2023-01-01 --end-date 2023-06-30
python octopus_lifetime_fetcher.py --start-date 2023-07-01 --end-date 2023-12-31
```

---

🌞 **Happy analyzing your solar energy data!** With lifetime data, you'll get much deeper insights into your energy patterns and solar system performance! 