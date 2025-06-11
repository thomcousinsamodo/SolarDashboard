# Data Refresh Guide (Database Version)

## 🗄️ **New Database Structure**

OctopusTracker now uses a SQLite database instead of CSV files:

```
📂 data/
├── 📦 energy_data.db (main database)
├── 📂 csv_backup/ (original CSV files)
└── 📂 logs/ (log files)
```

## 🔄 **Data Refresh Options**

### 1. **Consumption Data (30 days)**
- Fetches last 30 days of consumption data
- Updates database automatically
- Creates daily and monthly aggregates

### 2. **Pricing Data** 
- Fetches current tariff rates
- Saves to database pricing_raw table

### 3. **Complete Refresh**
- Refreshes both consumption and pricing
- Good for regular updates

### 4. **Lifetime Refresh**
- Downloads ALL available consumption data
- ⚠️ Can take 30+ minutes for large datasets
- Option to delete existing data first

## 🛠️ **Manual Database Operations**

```python
import database_utils

# Load data
daily_data = database_utils.load_consumption_data(table_name='consumption_daily')
pricing_data = database_utils.load_pricing_data()

# Save data
database_utils.save_consumption_data(df, 'consumption_raw')
database_utils.save_pricing_data(pricing_df)

# Get statistics
stats = database_utils.get_data_stats()

# Delete all consumption data
database_utils.delete_all_consumption_data()

# Create aggregates
database_utils.create_daily_aggregates()
database_utils.create_monthly_aggregates()
```

## 📊 **Database Schema**

### consumption_raw
- interval_start, interval_end, consumption, meter_type

### consumption_daily  
- date, total_kwh, meter_type

### consumption_monthly
- year_month, total_kwh, meter_type

### pricing_raw
- valid_from, valid_to, value_inc_vat, value_exc_vat, flow_direction

## 🔧 **Migration Commands**

If you need to re-migrate from CSV backups:
```bash
python migrate_to_database.py
```

If you need to update scripts for database usage:
```bash
python update_dashboard_for_database.py
```

## ✅ **Benefits of Database Approach**

- ⚡ **Faster queries** with indexed searches
- 🔒 **Data integrity** with transactions
- 💾 **Space efficient** (50% smaller than CSV)
- 🔄 **Concurrent access** for multiple processes
- 🗂️ **Better organization** with relational structure
