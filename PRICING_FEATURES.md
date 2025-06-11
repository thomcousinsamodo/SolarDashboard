# Solar Dashboard Pricing Features

## Overview
The solar dashboard now includes comprehensive financial analysis capabilities, allowing you to track not just energy consumption and generation, but also the actual costs and savings from your solar installation.

## 💰 Features Implemented

### 1. Price Configuration System
- **Energy Tariffs**: Configurable import rates (default: 28.62p/kWh) and export rates (default: 15.0p/kWh)
- **Standing Charges**: Daily standing charges (default: 60.10p/day) applied to import days only
- **Currency Support**: GBP with automatic pence/pounds conversion

### 2. Financial Summary Cards
Four new financial summary cards display:
- **Total Energy Bill**: Import costs + standing charges
- **Solar Export Earnings**: Total money earned from energy exports
- **Net Energy Cost**: Total bills minus export earnings
- **Solar Savings Rate**: Percentage of bill offset by export earnings

### 3. Price View Charts
Toggle "Price View (£)" in chart options to switch all charts from energy units to financial values:

#### Daily Overview Chart (Price Mode)
- **Grid Import Cost**: Shows daily import costs including standing charges
- **Solar Export Earnings**: Shows daily earnings from energy exports
- **Dual Information**: Hover shows both cost/earnings and energy amounts
- **Temperature Integration**: Still works with price view enabled

#### Net Flow Chart (Price Mode)
- **Net Energy Cost**: Import costs minus export earnings
- **Visual Indicators**: 
  - 🔴 Above zero: Net cost (money spent)
  - 🟢 Below zero: Net savings (money saved)
- **Rolling Averages**: 7-day trends for cost analysis

### 4. Rolling Average Support
Price views fully support rolling averages:
- Original price data shown as lighter traces
- Bold traces show rolling average trends
- Adaptive windows based on date range (7/14/30 days)

## 📊 Default UK Energy Rates (October 2024)

```python
DEFAULT_TARIFFS = {
    'import_rate': 28.62,         # pence per kWh
    'export_rate': 15.0,          # pence per kWh  
    'standing_charge_daily': 60.10 # pence per day
}
```

## 🔧 Technical Implementation

### Core Files
- `price_config.py`: Price calculation engine and tariff configuration
- `solar_dashboard.py`: Enhanced with price view toggles and financial metrics

### Key Components
- **PriceCalculator**: Handles all cost/earnings calculations
- **Chart Options**: Added "Price View (£)" toggle
- **Financial Cards**: Real-time cost summaries
- **Format Functions**: Currency display with proper £/pence formatting

### Chart Enhancements
- All main charts support price view mode
- Hover templates show both financial and energy data
- Chart titles and axis labels automatically update
- Color schemes remain consistent between energy and price views

## 💡 Usage Tips

### Viewing Costs
1. Enable "Price View (£)" in chart options
2. Charts switch to show costs/earnings instead of kWh
3. Hover over data points for detailed breakdowns
4. Financial summary cards update in real-time

### Understanding Net Cost Chart
- **Positive values**: Money spent (import costs exceed export earnings)
- **Negative values**: Money saved (export earnings exceed import costs)
- **Zero line**: Break-even point

### Rolling Averages with Pricing
- Enable both "Rolling Averages" and "Price View" for trend analysis
- Lighter traces show daily costs/earnings
- Bold traces show smoothed financial trends
- Adaptive windows provide appropriate smoothing for different time periods

## 🎯 Benefits

### For Solar Owners
- **ROI Tracking**: See actual financial returns from solar investment
- **Bill Analysis**: Understand how solar reduces energy bills
- **Savings Visualization**: Clear view of money saved through solar export
- **Trend Analysis**: Identify seasonal patterns in costs and savings

### for Energy Management
- **Cost Optimization**: Identify high-cost periods for usage adjustment
- **Export Strategy**: Understand when export earnings are highest
- **Budget Planning**: Predict future energy costs based on trends
- **Performance Monitoring**: Track financial efficiency of solar system

## 🔄 Future Enhancements

Potential additions for enhanced pricing features:
- **Variable Tariffs**: Support for time-of-use pricing (Agile Octopus, etc.)
- **Tariff Comparison**: Compare different energy suppliers/tariffs
- **Cost Forecasting**: Predict future costs based on historical patterns
- **ROI Calculator**: Solar installation payback period analysis
- **Export Strategy**: Optimal export timing recommendations

## 📈 Example Use Cases

### Monthly Bill Analysis
1. Set date range to previous month
2. Enable "Price View (£)"
3. Check financial summary cards for total costs/savings
4. Use net cost chart to see daily financial performance

### Seasonal Cost Comparison
1. Compare winter vs summer periods
2. Enable rolling averages for trend analysis
3. View how solar output affects seasonal bills
4. Identify periods of highest savings

### Solar Performance Evaluation
1. Track export earnings over time
2. Compare costs with/without solar (import vs export)
3. Calculate actual savings percentage
4. Monitor return on solar investment

---

The pricing features transform the dashboard from a simple energy monitor into a comprehensive financial analysis tool, helping solar owners understand the true economic impact of their renewable energy system. 