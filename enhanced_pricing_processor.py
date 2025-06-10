#!/usr/bin/env python3
"""
Enhanced Pricing Processor
Fetches historical pricing data and matches it with consumption data for accurate cost calculations
"""

import pandas as pd
import os
import argparse
from datetime import datetime, timedelta
from octopus_pricing_api import OctopusPricingAPI
import numpy as np


def process_consumption_with_real_pricing(consumption_file: str = 'octopus_consumption_raw.csv',
                                        output_file: str = 'octopus_consumption_with_pricing.csv',
                                        date_limit_days: int = None):
    """
    Process consumption data and add real historical pricing
    
    Args:
        consumption_file: Path to consumption CSV file
        output_file: Path for output CSV file with pricing
        date_limit_days: Limit processing to last N days (to avoid too many API calls)
    """
    
    print("🚀 Enhanced Pricing Processor")
    print("=" * 50)
    
    # Initialize API
    api = OctopusPricingAPI()
    
    if not api.authenticated:
        print("❌ No API credentials found!")
        print("   Set environment variables:")
        print("   export OCTOPUS_API_KEY='your_api_key'")
        print("   export OCTOPUS_ACCOUNT_NUMBER='A-AAAA1111'")
        return False
    
    # Load consumption data
    print(f"📁 Loading consumption data from {consumption_file}...")
    
    if not os.path.exists(consumption_file):
        print(f"❌ File not found: {consumption_file}")
        return False
    
    try:
        consumption_df = pd.read_csv(consumption_file)
        print(f"✅ Loaded {len(consumption_df)} consumption records")
        
        # Convert timestamps
        consumption_df['interval_start'] = pd.to_datetime(consumption_df['interval_start'], utc=True)
        consumption_df['interval_end'] = pd.to_datetime(consumption_df['interval_end'], utc=True)
        
        # Get date range
        start_date = consumption_df['interval_start'].min()
        end_date = consumption_df['interval_start'].max()
        
        print(f"📅 Data range: {start_date.date()} to {end_date.date()}")
        
        # Apply date limit if specified
        if date_limit_days:
            cutoff_date = datetime.now(consumption_df['interval_start'].dt.tz) - timedelta(days=date_limit_days)
            consumption_df = consumption_df[consumption_df['interval_start'] >= cutoff_date]
            start_date = consumption_df['interval_start'].min()
            print(f"📅 Limited to last {date_limit_days} days: {start_date.date()} to {end_date.date()}")
            print(f"📊 Filtered to {len(consumption_df)} records")
        
        if consumption_df.empty:
            print("❌ No consumption data after filtering")
            return False
            
    except Exception as e:
        print(f"❌ Error loading consumption data: {e}")
        return False
    
    # Get tariff information
    print("\n🔍 Getting tariff information...")
    tariffs = api.get_account_tariffs()
    
    if not tariffs:
        print("❌ Could not retrieve tariff information")
        return False
    
    # Identify import and export tariffs
    import_tariff = None
    export_tariff = None
    
    for tariff in tariffs:
        if tariff.is_export:
            export_tariff = tariff
        else:
            import_tariff = tariff
    
    if not import_tariff:
        print("❌ No import tariff found")
        return False
    
    print(f"📊 Import tariff: {import_tariff.tariff_code} (Variable: {import_tariff.is_variable})")
    if export_tariff:
        print(f"📊 Export tariff: {export_tariff.tariff_code} (Variable: {export_tariff.is_variable})")
    
    # Fetch pricing data
    print(f"\n💰 Fetching historical pricing data...")
    
    # Get import pricing data
    import_pricing_df = pd.DataFrame()
    if import_tariff.is_variable:
        print(f"🔍 Fetching variable import pricing for {import_tariff.tariff_code}...")
        import_pricing_df = api.get_historical_pricing_data(
            import_tariff.tariff_code, 
            start_date, 
            end_date,
            is_export=False
        )
    else:
        print(f"📊 Using fixed import rate: {import_tariff.unit_rate}p/kWh")
        # Create a simple pricing DataFrame for fixed rates
        import_pricing_df = pd.DataFrame([{
            'valid_from': start_date,
            'valid_to': end_date + timedelta(days=1),
            'rate_inc_vat': import_tariff.unit_rate,
            'rate_exc_vat': import_tariff.unit_rate / 1.05
        }])
    
    # Get export pricing data
    export_pricing_df = pd.DataFrame()
    if export_tariff:
        if export_tariff.is_variable:
            print(f"🔍 Fetching variable export pricing for {export_tariff.tariff_code}...")
            export_pricing_df = api.get_historical_pricing_data(
                export_tariff.tariff_code, 
                start_date, 
                end_date,
                is_export=True
            )
        else:
            print(f"📊 Using fixed export rate: {export_tariff.unit_rate}p/kWh")
            # Create a simple pricing DataFrame for fixed rates
            export_pricing_df = pd.DataFrame([{
                'valid_from': start_date,
                'valid_to': end_date + timedelta(days=1),
                'rate_inc_vat': export_tariff.unit_rate,
                'rate_exc_vat': export_tariff.unit_rate / 1.05
            }])
    
    # Match consumption with pricing
    print(f"\n🔗 Matching consumption data with pricing...")
    enhanced_df = api.match_consumption_with_pricing(
        consumption_df,
        import_pricing_df,
        export_pricing_df,
        import_tariff.standing_charge
    )
    
    if enhanced_df.empty:
        print("❌ Failed to match consumption with pricing")
        return False
    
    # Calculate summary statistics
    print(f"\n📊 Pricing Analysis Summary:")
    
    # Import analysis
    import_data = enhanced_df[enhanced_df['meter_type'] == 'import']
    if not import_data.empty:
        total_import_kwh = import_data['consumption'].sum()
        total_import_cost = import_data['cost_inc_vat'].sum()
        total_standing_charges = import_data['standing_charge'].sum()
        avg_import_rate = (total_import_cost / total_import_kwh) if total_import_kwh > 0 else 0
        
        print(f"   🔴 Import:")
        print(f"      Energy: {total_import_kwh:.2f} kWh")
        print(f"      Cost: £{total_import_cost/100:.2f}")
        print(f"      Standing charges: £{total_standing_charges/100:.2f}")
        print(f"      Average rate: {avg_import_rate:.2f}p/kWh")
        
        if import_tariff.is_variable:
            min_rate = import_data['rate_inc_vat'].min()
            max_rate = import_data['rate_inc_vat'].max()
            print(f"      Rate range: {min_rate:.2f}p - {max_rate:.2f}p/kWh")
    
    # Export analysis
    export_data = enhanced_df[enhanced_df['meter_type'] == 'export']
    if not export_data.empty:
        total_export_kwh = export_data['consumption'].sum()
        total_export_earnings = export_data['cost_inc_vat'].sum()
        avg_export_rate = (total_export_earnings / total_export_kwh) if total_export_kwh > 0 else 0
        
        print(f"   🟢 Export:")
        print(f"      Energy: {total_export_kwh:.2f} kWh")
        print(f"      Earnings: £{total_export_earnings/100:.2f}")
        print(f"      Average rate: {avg_export_rate:.2f}p/kWh")
        
        if export_tariff and export_tariff.is_variable:
            min_rate = export_data['rate_inc_vat'].min()
            max_rate = export_data['rate_inc_vat'].max()
            print(f"      Rate range: {min_rate:.2f}p - {max_rate:.2f}p/kWh")
    
    # Net cost
    if not import_data.empty and not export_data.empty:
        total_bill = total_import_cost + total_standing_charges
        net_cost = total_bill - total_export_earnings
        savings_rate = (total_export_earnings / total_bill * 100) if total_bill > 0 else 0
        
        print(f"   💰 Summary:")
        print(f"      Total bill: £{total_bill/100:.2f}")
        print(f"      Export earnings: £{total_export_earnings/100:.2f}")
        print(f"      Net cost: £{net_cost/100:.2f}")
        print(f"      Solar savings: {savings_rate:.1f}%")
    
    # Save enhanced data
    print(f"\n💾 Saving enhanced data to {output_file}...")
    
    # Round pricing columns for readability
    price_columns = ['rate_inc_vat', 'rate_exc_vat', 'cost_inc_vat', 'cost_exc_vat', 'standing_charge']
    for col in price_columns:
        if col in enhanced_df.columns:
            enhanced_df[col] = enhanced_df[col].round(4)
    
    try:
        enhanced_df.to_csv(output_file, index=False)
        print(f"✅ Enhanced data saved with {len(enhanced_df)} records")
        
        # Show sample of enhanced data
        print(f"\n📋 Sample of enhanced data:")
        sample_cols = ['interval_start', 'consumption', 'meter_type', 'rate_inc_vat', 'cost_inc_vat']
        available_cols = [col for col in sample_cols if col in enhanced_df.columns]
        print(enhanced_df[available_cols].head().to_string(index=False))
        
    except Exception as e:
        print(f"❌ Error saving enhanced data: {e}")
        return False
    
    print(f"\n🎉 Processing complete!")
    print(f"   📁 Original file: {consumption_file}")
    print(f"   📁 Enhanced file: {output_file}")
    print(f"   💰 Real pricing data included for accurate cost calculations")
    
    return True


def create_daily_summary_with_pricing(enhanced_file: str = 'octopus_consumption_with_pricing.csv',
                                     daily_file: str = 'octopus_consumption_daily_with_pricing.csv'):
    """Create daily summary with real pricing data"""
    
    print(f"\n📊 Creating daily summary with pricing...")
    
    if not os.path.exists(enhanced_file):
        print(f"❌ Enhanced file not found: {enhanced_file}")
        return False
    
    try:
        df = pd.read_csv(enhanced_file)
        df['interval_start'] = pd.to_datetime(df['interval_start'], utc=True)
        
        # Convert to local timezone for daily grouping
        df['date_local'] = df['interval_start'].dt.tz_convert('Europe/London').dt.date
        
        # Group by date and meter type
        daily_summary = df.groupby(['date_local', 'meter_type']).agg({
            'consumption': ['sum', 'count'],
            'cost_inc_vat': 'sum',
            'cost_exc_vat': 'sum',
            'standing_charge': 'sum',
            'rate_inc_vat': ['min', 'max', 'mean']
        }).round(4)
        
        # Flatten column names
        daily_summary.columns = [
            'total_kwh', 'readings_count',
            'total_cost_inc_vat', 'total_cost_exc_vat', 'total_standing_charge',
            'min_rate', 'max_rate', 'avg_rate'
        ]
        
        daily_summary.reset_index(inplace=True)
        daily_summary.rename(columns={'date_local': 'date'}, inplace=True)
        
        # Save daily summary
        daily_summary.to_csv(daily_file, index=False)
        print(f"✅ Daily summary saved with {len(daily_summary)} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating daily summary: {e}")
        return False


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description='Process consumption data with real historical pricing')
    parser.add_argument('--input', type=str, default='octopus_consumption_raw.csv', 
                       help='Input consumption CSV file')
    parser.add_argument('--output', type=str, default='octopus_consumption_with_pricing.csv',
                       help='Output CSV file with pricing')
    parser.add_argument('--days', type=int, help='Limit to last N days (to reduce API calls)')
    parser.add_argument('--daily-summary', action='store_true', 
                       help='Also create daily summary with pricing')
    
    args = parser.parse_args()
    
    # Check environment variables
    api_key = os.getenv('OCTOPUS_API_KEY')
    account_number = os.getenv('OCTOPUS_ACCOUNT_NUMBER')
    
    if not api_key or not account_number:
        print("❌ Missing environment variables!")
        print("   Set these before running:")
        print("   export OCTOPUS_API_KEY='your_api_key'")
        print("   export OCTOPUS_ACCOUNT_NUMBER='A-AAAA1111'")
        return
    
    # Process consumption with pricing
    success = process_consumption_with_real_pricing(
        consumption_file=args.input,
        output_file=args.output,
        date_limit_days=args.days
    )
    
    if not success:
        print("❌ Processing failed")
        return
    
    # Create daily summary if requested
    if args.daily_summary:
        create_daily_summary_with_pricing(args.output)
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Review the enhanced data in {args.output}")
    print(f"   2. Use this data for accurate cost analysis")
    print(f"   3. Compare with your Octopus Energy bills")
    print(f"   4. Update your dashboard to use the new pricing data")


if __name__ == "__main__":
    main() 