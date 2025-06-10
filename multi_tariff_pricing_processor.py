#!/usr/bin/env python3
"""
Multi-Tariff Pricing Processor
Handles consumption data with multiple tariff periods and rate structures over time
"""

import pandas as pd
import os
import argparse
from datetime import datetime, timedelta
from octopus_pricing_api import OctopusPricingAPI
from tariff_configuration import TariffConfigurationManager, TariffPeriod
import numpy as np


class MultiTariffPricingProcessor:
    """Process consumption data with multiple tariff periods"""
    
    def __init__(self, config_file: str = 'tariff_config.json'):
        self.config_manager = TariffConfigurationManager(config_file)
        self.api = OctopusPricingAPI()
        
        if not self.api.authenticated:
            print("❌ No API credentials found!")
            print("   Set environment variables:")
            print("   export OCTOPUS_API_KEY='your_api_key'")
            print("   export OCTOPUS_ACCOUNT_NUMBER='A-AAAA1111'")
            return
        
        print("✅ Multi-tariff pricing processor initialized")
    
    def process_consumption_with_multi_tariff_pricing(self, 
                                                    consumption_file: str = 'octopus_consumption_raw.csv',
                                                    output_file: str = 'octopus_consumption_multi_tariff_pricing.csv',
                                                    date_limit_days: int = None):
        """
        Process consumption data with multiple tariff periods
        
        Args:
            consumption_file: Path to consumption CSV file
            output_file: Path for output CSV file with pricing
            date_limit_days: Limit processing to last N days
        """
        
        print("🚀 Multi-Tariff Pricing Processor")
        print("=" * 60)
        
        if not self.api.authenticated:
            return False
        
        # Load consumption data
        print(f"📁 Loading consumption data from {consumption_file}...")
        
        if not os.path.exists(consumption_file):
            print(f"❌ File not found: {consumption_file}")
            return False
        
        try:
            consumption_df = pd.read_csv(consumption_file)
            consumption_df['interval_start'] = pd.to_datetime(consumption_df['interval_start'], utc=True)
            consumption_df['interval_end'] = pd.to_datetime(consumption_df['interval_end'], utc=True)
            
            print(f"✅ Loaded {len(consumption_df)} consumption records")
            
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
        
        # Show tariff configuration
        print(f"\n📋 Using tariff configuration:")
        self.config_manager.print_configuration()
        
        # Process each tariff period separately
        print(f"\n🔄 Processing consumption by tariff periods...")
        
        # Initialize result DataFrame
        enhanced_df = consumption_df.copy()
        enhanced_df['tariff_name'] = ""
        enhanced_df['tariff_code'] = ""
        enhanced_df['rate_inc_vat'] = None
        enhanced_df['rate_exc_vat'] = None
        enhanced_df['cost_exc_vat'] = None
        enhanced_df['cost_inc_vat'] = None
        enhanced_df['standing_charge'] = 0.0
        
        # Process import tariffs
        print(f"\n📊 Processing import tariffs...")
        import_periods = self.config_manager.get_tariff_periods_for_range(
            start_date, end_date, is_export=False
        )
        
        for period, period_start, period_end in import_periods:
            print(f"\n   🔍 Processing {period.name}")
            print(f"      📅 Period: {period_start.date()} to {period_end.date()}")
            
            # Filter consumption data for this period
            period_mask = (
                (enhanced_df['meter_type'] == 'import') &
                (enhanced_df['interval_start'] >= period_start) &
                (enhanced_df['interval_start'] <= period_end)
            )
            
            period_records = period_mask.sum()
            if period_records == 0:
                print(f"      ⚠️  No consumption data for this period")
                continue
            
            print(f"      📊 Processing {period_records} records")
            
            # Get pricing data for this period
            if period.is_variable:
                print(f"      🔍 Fetching variable pricing data...")
                pricing_df = self.api.get_historical_pricing_data(
                    period.tariff_code, period_start, period_end, is_export=False
                )
                
                if pricing_df.empty:
                    print(f"      ⚠️  No pricing data available, using fallback rate")
                    pricing_df = self._create_fallback_pricing_df(period, period_start, period_end)
            else:
                print(f"      📊 Using fixed rate: {period.fixed_rate}p/kWh")
                pricing_df = self._create_fixed_rate_pricing_df(period, period_start, period_end)
            
            # Apply pricing to consumption data
            self._apply_pricing_to_period(enhanced_df, period_mask, period, pricing_df)
        
        # Process export tariffs
        print(f"\n📊 Processing export tariffs...")
        export_periods = self.config_manager.get_tariff_periods_for_range(
            start_date, end_date, is_export=True
        )
        
        for period, period_start, period_end in export_periods:
            print(f"\n   🔍 Processing {period.name}")
            print(f"      📅 Period: {period_start.date()} to {period_end.date()}")
            
            # Filter consumption data for this period
            period_mask = (
                (enhanced_df['meter_type'] == 'export') &
                (enhanced_df['interval_start'] >= period_start) &
                (enhanced_df['interval_start'] <= period_end)
            )
            
            period_records = period_mask.sum()
            if period_records == 0:
                print(f"      ⚠️  No consumption data for this period")
                continue
            
            print(f"      📊 Processing {period_records} records")
            
            # Get pricing data for this period
            if period.is_variable:
                print(f"      🔍 Fetching variable pricing data...")
                pricing_df = self.api.get_historical_pricing_data(
                    period.tariff_code, period_start, period_end, is_export=True
                )
                
                if pricing_df.empty:
                    print(f"      ⚠️  No pricing data available, using fallback rate")
                    pricing_df = self._create_fallback_pricing_df(period, period_start, period_end)
            else:
                print(f"      📊 Using fixed rate: {period.fixed_rate}p/kWh")
                pricing_df = self._create_fixed_rate_pricing_df(period, period_start, period_end)
            
            # Apply pricing to consumption data (no standing charge for export)
            self._apply_pricing_to_period(enhanced_df, period_mask, period, pricing_df, include_standing_charge=False)
        
        # Calculate summary statistics
        self._print_summary_statistics(enhanced_df)
        
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
            sample_cols = ['interval_start', 'consumption', 'meter_type', 'tariff_name', 'rate_inc_vat', 'cost_inc_vat']
            available_cols = [col for col in sample_cols if col in enhanced_df.columns]
            print(enhanced_df[available_cols].head().to_string(index=False))
            
        except Exception as e:
            print(f"❌ Error saving enhanced data: {e}")
            return False
        
        print(f"\n🎉 Multi-tariff processing complete!")
        print(f"   📁 Original file: {consumption_file}")
        print(f"   📁 Enhanced file: {output_file}")
        print(f"   💰 Accurate pricing across multiple tariff periods")
        
        return True
    
    def _create_fixed_rate_pricing_df(self, period: TariffPeriod, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Create pricing DataFrame for fixed rate tariffs"""
        return pd.DataFrame([{
            'valid_from': start_date,
            'valid_to': end_date + timedelta(hours=1),
            'rate_inc_vat': period.fixed_rate,
            'rate_exc_vat': period.fixed_rate / 1.05
        }])
    
    def _create_fallback_pricing_df(self, period: TariffPeriod, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Create fallback pricing DataFrame when API data is unavailable"""
        fallback_rate = period.fixed_rate or 28.62  # Use configured rate or default
        return pd.DataFrame([{
            'valid_from': start_date,
            'valid_to': end_date + timedelta(hours=1),
            'rate_inc_vat': fallback_rate,
            'rate_exc_vat': fallback_rate / 1.05
        }])
    
    def _apply_pricing_to_period(self, enhanced_df: pd.DataFrame, period_mask: pd.Series, 
                               period: TariffPeriod, pricing_df: pd.DataFrame, 
                               include_standing_charge: bool = True):
        """Apply pricing data to consumption records for a specific period"""
        
        for idx in enhanced_df[period_mask].index:
            interval_start = enhanced_df.at[idx, 'interval_start']
            consumption = enhanced_df.at[idx, 'consumption']
            
            # Find matching pricing period
            matching_rates = pricing_df[
                (pricing_df['valid_from'] <= interval_start) & 
                (pricing_df['valid_to'] > interval_start)
            ]
            
            if not matching_rates.empty:
                # Use the first matching rate
                rate_inc_vat = matching_rates.iloc[0]['rate_inc_vat']
                rate_exc_vat = matching_rates.iloc[0]['rate_exc_vat']
                
                # Calculate costs
                cost_inc_vat = consumption * rate_inc_vat
                cost_exc_vat = consumption * rate_exc_vat
                
                # Add standing charge for import records
                standing_charge = 0.0
                if include_standing_charge and period.standing_charge:
                    # Distribute daily standing charge across 48 half-hourly periods
                    standing_charge = period.standing_charge / 48.0
                
                # Update the result DataFrame
                enhanced_df.at[idx, 'tariff_name'] = period.name
                enhanced_df.at[idx, 'tariff_code'] = period.tariff_code
                enhanced_df.at[idx, 'rate_inc_vat'] = rate_inc_vat
                enhanced_df.at[idx, 'rate_exc_vat'] = rate_exc_vat
                enhanced_df.at[idx, 'cost_inc_vat'] = cost_inc_vat
                enhanced_df.at[idx, 'cost_exc_vat'] = cost_exc_vat
                enhanced_df.at[idx, 'standing_charge'] = standing_charge
    
    def _print_summary_statistics(self, enhanced_df: pd.DataFrame):
        """Print summary statistics by tariff period"""
        
        print(f"\n📊 Multi-Tariff Analysis Summary:")
        print("=" * 60)
        
        # Group by tariff and meter type
        for tariff_name in enhanced_df['tariff_name'].unique():
            if not tariff_name:  # Skip empty tariff names
                continue
                
            tariff_data = enhanced_df[enhanced_df['tariff_name'] == tariff_name]
            
            print(f"\n🏷️  {tariff_name}")
            
            # Import analysis
            import_data = tariff_data[tariff_data['meter_type'] == 'import']
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
                
                if len(import_data['rate_inc_vat'].unique()) > 1:
                    min_rate = import_data['rate_inc_vat'].min()
                    max_rate = import_data['rate_inc_vat'].max()
                    print(f"      Rate range: {min_rate:.2f}p - {max_rate:.2f}p/kWh")
            
            # Export analysis
            export_data = tariff_data[tariff_data['meter_type'] == 'export']
            if not export_data.empty:
                total_export_kwh = export_data['consumption'].sum()
                total_export_earnings = export_data['cost_inc_vat'].sum()
                avg_export_rate = (total_export_earnings / total_export_kwh) if total_export_kwh > 0 else 0
                
                print(f"   🟢 Export:")
                print(f"      Energy: {total_export_kwh:.2f} kWh")
                print(f"      Earnings: £{total_export_earnings/100:.2f}")
                print(f"      Average rate: {avg_export_rate:.2f}p/kWh")
                
                if len(export_data['rate_inc_vat'].unique()) > 1:
                    min_rate = export_data['rate_inc_vat'].min()
                    max_rate = export_data['rate_inc_vat'].max()
                    print(f"      Rate range: {min_rate:.2f}p - {max_rate:.2f}p/kWh")
        
        # Overall summary
        total_import_cost = enhanced_df[enhanced_df['meter_type'] == 'import']['cost_inc_vat'].sum()
        total_standing_charges = enhanced_df[enhanced_df['meter_type'] == 'import']['standing_charge'].sum()
        total_export_earnings = enhanced_df[enhanced_df['meter_type'] == 'export']['cost_inc_vat'].sum()
        
        if total_import_cost > 0 and total_export_earnings > 0:
            total_bill = total_import_cost + total_standing_charges
            net_cost = total_bill - total_export_earnings
            savings_rate = (total_export_earnings / total_bill * 100) if total_bill > 0 else 0
            
            print(f"\n💰 Overall Summary:")
            print(f"   Total bill: £{total_bill/100:.2f}")
            print(f"   Export earnings: £{total_export_earnings/100:.2f}")
            print(f"   Net cost: £{net_cost/100:.2f}")
            print(f"   Solar savings: {savings_rate:.1f}%")


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description='Process consumption data with multiple tariff periods')
    parser.add_argument('--input', type=str, default='octopus_consumption_raw.csv', 
                       help='Input consumption CSV file')
    parser.add_argument('--output', type=str, default='octopus_consumption_multi_tariff_pricing.csv',
                       help='Output CSV file with pricing')
    parser.add_argument('--config', type=str, default='tariff_config.json',
                       help='Tariff configuration file')
    parser.add_argument('--days', type=int, help='Limit to last N days (to reduce API calls)')
    parser.add_argument('--setup', action='store_true', help='Run interactive tariff setup')
    
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
    
    if args.setup:
        # Run interactive setup
        from tariff_configuration import TariffConfigurationManager
        manager = TariffConfigurationManager(args.config)
        manager.interactive_setup()
        return
    
    # Process consumption with multi-tariff pricing
    processor = MultiTariffPricingProcessor(args.config)
    success = processor.process_consumption_with_multi_tariff_pricing(
        consumption_file=args.input,
        output_file=args.output,
        date_limit_days=args.days
    )
    
    if not success:
        print("❌ Processing failed")
        return
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Review the enhanced data in {args.output}")
    print(f"   2. Check tariff periods and rates match your expectations")
    print(f"   3. Compare costs between different tariff periods")
    print(f"   4. Use this data for accurate multi-period cost analysis")


if __name__ == "__main__":
    main() 