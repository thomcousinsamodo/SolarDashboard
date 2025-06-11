# 💰 Spending Dashboard

The Spending Dashboard provides detailed financial analysis of your energy usage by combining half-hourly consumption data with tariff rates to show actual costs and earnings.

## 🎯 What It Shows

### Summary Metrics
- **Total Import Cost**: How much you've spent buying electricity from the grid
- **Total Export Earnings**: How much you've earned selling solar energy back to the grid
- **Net Cost/Savings**: Your overall energy balance (positive = cost, negative = savings)
- **Daily Average**: Average daily cost or savings over the selected period

### Interactive Charts
1. **Daily Spending Timeline**: Shows daily import costs, export earnings, and net spending over time
2. **Hourly Analysis**: Average spending/earnings by hour of day to identify peak cost periods
3. **Rate Comparison**: Visualizes import vs export rates over time

## 🚀 Getting Started

### Prerequisites
- Consumption data (from octopus_energy_fetcher.py or octopus_lifetime_fetcher.py)
- Pricing data (from tariff tracker and generate_pricing_data.py)
- Both datasets must cover overlapping time periods

### Running the Dashboard
```bash
python spending_dashboard.py
```

The dashboard will be available at: **http://localhost:5001**

### Accessing from Main Dashboard
The main dashboard (http://localhost:5000) includes a "Spending Dashboard" button in the top navigation.

## 📊 How It Works

### Data Matching Process
1. **Loads consumption data** from the `consumption_raw` table (half-hourly intervals)
2. **Loads pricing data** from the `pricing_raw` table (half-hourly rates)
3. **Matches by datetime** using `interval_start` for consumption and `datetime` for pricing
4. **Calculates costs** by multiplying consumption (kWh) × rate (pence/kWh)
5. **Separates import vs export** to show costs vs earnings

### Rate Matching Logic
- Uses `pd.merge_asof` with `direction='backward'` to find the most recent applicable rate
- Handles different tariff periods and rate changes automatically
- Separates import and export flows for accurate cost calculation

## 🔧 Key Features

### Date Range Selection
- **Quick buttons**: 7 days, 30 days, 90 days
- **Custom range**: Pick any start and end date
- **Real-time updates**: Charts refresh when date range changes

### Financial Insights
- **Granular cost tracking**: See exactly when you spend/earn money
- **Peak identification**: Find your most expensive hours/days
- **Rate analysis**: Compare import vs export rate trends
- **Period comparisons**: Understand seasonal cost variations

### Interactive Visualizations
- **Hover details**: See exact costs, rates, and consumption amounts
- **Responsive design**: Works on desktop, tablet, and mobile
- **Export earnings shown as negative**: Clearly distinguish costs from earnings

## 📈 Understanding the Charts

### Timeline Chart
- **Red line (Import Cost)**: Money spent buying electricity
- **Green line (Export Earnings)**: Money earned selling electricity (shown as negative)
- **Yellow dashed line (Net)**: Your overall energy balance
- **Zero line**: Break-even point

### Hourly Chart
- **Red bars**: Average import costs by hour
- **Green bars**: Average export earnings by hour (shown as negative)
- **Peak hours**: Identify when electricity is most expensive

### Rate Comparison
- **Red dots**: Import rates over time
- **Green dots**: Export rates over time
- **Rate spreads**: See the difference between what you pay vs what you earn

## 🛠️ Technical Details

### Database Schema Requirements
The dashboard expects these database tables:

**consumption_raw**:
- `consumption` (REAL): Energy amount in kWh
- `interval_start` (TEXT): Start time of half-hour period
- `interval_end` (TEXT): End time of half-hour period  
- `meter_type` (TEXT): 'import' or 'export'

**pricing_raw**:
- `datetime` (TEXT): Half-hour period datetime
- `flow_direction` (TEXT): 'import' or 'export'
- `rate_inc_vat` (REAL): Rate including VAT in pence/kWh
- `period_name` (TEXT): Tariff period identifier

### Performance Considerations
- Automatically samples large datasets (1000 points max) for rate charts
- Uses efficient SQL queries with date filtering
- Caches chart data in browser for responsive interactions

## 🚨 Troubleshooting

### "No Spending Data Available"
**Possible causes:**
1. **No consumption data**: Run consumption data fetcher first
2. **No pricing data**: Ensure tariff tracker has pricing data for the period
3. **Date mismatch**: Consumption and pricing data don't overlap
4. **Missing rates**: Pricing data exists but rates are null/empty

**Solutions:**
1. Go to main dashboard and refresh consumption data
2. Use tariff tracker to refresh pricing data  
3. Run `generate_pricing_data.py` to ensure pricing database is populated
4. Check date ranges - ensure both datasets cover the same period

### Charts Not Loading
**Check:**
1. Browser console for JavaScript errors
2. Network tab for failed API calls
3. Date range selection (both start and end dates required)

### Incorrect Cost Calculations
**Verify:**
1. Consumption data units (should be kWh)
2. Pricing data units (should be pence/kWh including VAT)
3. Date/time formats match between datasets
4. Meter types correctly identify import vs export

## 🔗 Integration

### With Main Dashboard
- Accessible via navigation button
- Runs on separate port (5001) to avoid conflicts
- Uses same database and credential system

### With Tariff Tracker
- Leverages pricing data from tariff tracker
- Inherits tariff period definitions and rate calculations
- Automatically handles multiple tariff periods

### With Data Fetchers
- Works with data from octopus_energy_fetcher.py
- Compatible with octopus_lifetime_fetcher.py
- Uses database storage for optimal performance

## 📱 Mobile Support

The dashboard is fully responsive and optimized for:
- **Desktop**: Full feature access with side-by-side charts
- **Tablet**: Responsive layout with stacked charts
- **Mobile**: Touch-friendly controls and readable text

## 🔐 Security

- Uses same credential manager as main dashboard
- No additional API keys required
- Operates on local network only (localhost:5001)
- Database access through existing database_utils.py

---

**Next Steps**: Consider adding export options (CSV/PDF), bill prediction features, and tariff comparison tools! 