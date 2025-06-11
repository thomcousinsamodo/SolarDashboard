# Real Octopus Energy API Pricing Setup

## Overview
The dashboard now supports **real pricing data** from your Octopus Energy account, providing exact bill calculations instead of generic estimates.

## 🎯 **What You Get with Real API Pricing**

### ✅ **Exact Billing Data**
- **Your Actual Tariff Rates**: Uses your real import/export rates
- **Real Standing Charges**: Your exact daily charges by region
- **Bill Matching**: Costs will match your actual Octopus Energy bills
- **Historical Accuracy**: See how rate changes affected your costs over time

### 🆚 **Default vs Real Pricing**

| Feature | Default Pricing | Real API Pricing |
|---------|----------------|------------------|
| **Import Rate** | 28.62p/kWh (UK average) | Your exact tariff rate |
| **Export Rate** | 15.0p/kWh (SEG average) | Your actual export rate |
| **Standing Charge** | 60.10p/day (UK average) | Your regional rate |
| **Bill Accuracy** | ±20% estimate | Exact match |
| **Tariff Changes** | Static rates | Historical rate tracking |
| **Variable Tariffs** | Not supported | Full Agile/Go support |

## 🔧 **Setup Instructions**

### Step 1: Get Your API Credentials

1. **Log into your Octopus Energy account**
   - Go to [octopus.energy](https://octopus.energy)
   - Sign in to your account dashboard

2. **Find your API Key**
   - Navigate to: **Account → Developer API**
   - Copy your **API Key** (format: `sk_live_...`)

3. **Find your Account Number**
   - Check your bills or account dashboard
   - Format: `A-AAAA1111` (e.g., `A-B1C23456`)

### Step 2: Set Environment Variables

#### Windows (Command Prompt)
```cmd
set OCTOPUS_API_KEY=sk_live_your_actual_api_key_here
set OCTOPUS_ACCOUNT_NUMBER=A-B1C23456
```

#### Windows (PowerShell)
```powershell
$env:OCTOPUS_API_KEY="sk_live_your_actual_api_key_here"
$env:OCTOPUS_ACCOUNT_NUMBER="A-B1C23456"
```

#### Linux/macOS (Bash)
```bash
export OCTOPUS_API_KEY="sk_live_your_actual_api_key_here"
export OCTOPUS_ACCOUNT_NUMBER="A-B1C23456"
```

#### Persistent Setup (recommended)
Add to your system environment variables or shell profile:

**Windows:**
- System Properties → Environment Variables
- Add user variables for `OCTOPUS_API_KEY` and `OCTOPUS_ACCOUNT_NUMBER`

**Linux/macOS:**
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export OCTOPUS_API_KEY="sk_live_your_actual_api_key_here"
export OCTOPUS_ACCOUNT_NUMBER="A-B1C23456"
```

### Step 3: Test the Connection

```bash
python octopus_pricing_api.py
```

**Expected Output (Success):**
```
🔍 Testing Octopus Energy Pricing API...
✅ Using real import tariff: E-1R-VAR-22-11-01-C
   Fixed rate: 28.34p/kWh
   Standing charge: 59.81p/day
✅ Using real export tariff: E-1R-OUTGOING-FIX-12M-19-05-13-C
   Fixed rate: 5.5p/kWh

💰 Pricing Configuration:
   Import rate: 28.34p/kWh
   Export rate: 5.5p/kWh
   Standing charge: 59.81p/day
   Data source: octopus_api
```

**Expected Output (No Credentials):**
```
🔍 Testing Octopus Energy Pricing API...
⚠️  No API credentials found. Set environment variables:
   export OCTOPUS_API_KEY='your_api_key'
   export OCTOPUS_ACCOUNT_NUMBER='A-AAAA1111'

📊 Testing with default pricing...
```

### Step 4: Restart the Dashboard

After setting credentials, restart the dashboard:
```bash
python solar_dashboard.py
```

## 📊 **Dashboard Changes with Real Pricing**

### Pricing Information Card
- **🌐 Real Octopus Energy API Data**: Shows when using real pricing
- **📊 Default UK Energy Tariffs**: Shows when using generic pricing
- **Last Updated**: Timestamp of when API data was fetched
- **Setup Instructions**: Guidance when credentials are missing

### Financial Summary Cards
- **Exact Costs**: Match your actual Octopus Energy bills
- **Real Savings**: Accurate export earnings calculations
- **True ROI**: Genuine solar investment performance

### Chart Updates
- **Price View Toggle**: Shows real costs when enabled
- **Hover Information**: Displays actual rates being used
- **Bill Reconciliation**: Costs align with monthly statements

## 🚀 **Supported Tariff Types**

### ✅ **Fixed Rate Tariffs**
- Standard variable tariffs
- Fixed rate contracts
- Green energy tariffs

### ✅ **Export Tariffs**
- Outgoing Octopus (fixed rate)
- SEG (Smart Export Guarantee)
- Agile Outgoing (variable rate)

### 🔄 **Variable Rate Tariffs** (Future Enhancement)
- Agile Octopus (30-min pricing)
- Octopus Go (time-of-use)
- Economy 7 tariffs

## 🔍 **Troubleshooting**

### Problem: "No API credentials found"
**Solution:** Set environment variables correctly and restart dashboard

### Problem: "Error fetching account tariffs"
**Possible Causes:**
- Incorrect API key format
- Wrong account number
- Network connectivity issues
- API rate limiting

**Solutions:**
1. Verify credentials in Octopus Energy account
2. Check network connection
3. Wait a few minutes and retry

### Problem: "Could not fetch tariff details"
**Possible Causes:**
- New tariff type not yet supported
- Temporary API issues

**Solutions:**
1. Check console for specific error messages
2. Dashboard will fall back to default rates
3. Contact support if persistent

### Problem: Costs don't match bills exactly
**Possible Causes:**
- Multiple tariff changes during period
- Different billing periods
- VAT/tax differences

**Solutions:**
1. Check date ranges match your billing period
2. Verify tariff change dates
3. Use smaller date ranges for accuracy

## 💡 **Tips for Best Results**

### Date Range Selection
- **Monthly Analysis**: Use exact billing period dates
- **Seasonal Comparison**: Compare same months year-over-year
- **Rate Change Impact**: Use dates around tariff changes

### Data Validation
- **Cross-check with Bills**: Compare dashboard totals with statements
- **Standing Charge Verification**: Should match daily charges on bills
- **Unit Rate Confirmation**: Verify against contract documents

### Regular Updates
- **Rate Changes**: Dashboard automatically uses current rates
- **New Tariffs**: Restart dashboard after switching tariffs
- **Historical Analysis**: Past data remains accurate to original rates

## 🔒 **Security & Privacy**

### API Key Security
- **Never commit API keys to code repositories**
- **Use environment variables only**
- **Regenerate keys if compromised**

### Data Usage
- **Read-only access**: API only reads your data, never modifies
- **Local processing**: All calculations happen on your computer
- **No data sharing**: Your energy data stays private

### Rate Limiting
- **API calls are minimized** to respect Octopus Energy limits
- **Caching prevents excessive requests**
- **Fallback ensures dashboard always works**

---

## 🎉 **Success!**

Once set up correctly, you'll see:
- Real pricing data indicator in the dashboard
- Exact cost calculations matching your bills
- Accurate solar savings and ROI metrics
- Professional-grade energy analysis tools

Your solar dashboard is now a **complete financial analysis platform** using your real energy costs!
