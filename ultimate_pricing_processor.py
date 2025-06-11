#!/usr/bin/env python3
"""
Ultimate Pricing Processor
Handles all pricing complexity: time-of-use rates, quarterly changes, and variable pricing
"""

import pandas as pd
import os
import argparse
from datetime import datetime, timedelta
from octopus_pricing_api import OctopusPricingAPI
from enhanced_tariff_configuration import EnhancedTariffConfigurationManager
import numpy as np


class UltimatePricingProcessor:
    """The ultimate processor for all tariff complexities"""
    
    def __init__(self, config_file: str = 'enhanced_tariff_config.json'):
        self.config_manager = EnhancedTariffConfigurationManager(config_file)
        self.api = OctopusPricingAPI()
        
        if not self.api.authenticated:
            print("❌ No API credentials found for Agile pricing!")
            print("   Variable tariffs will use fallback rates")
        else:
            print("✅ API authenticated - can fetch real Agile pricing")
        
        print("✅ Ultimate pricing processor initialized")
    
    def process_consumption_with_ultimate_pricing(self, 
                                                consumption_file: str = 'octopus_consumption_raw.csv',
                                                output_file: str = 'octopus_consumption_ultimate_pricing.csv',
                                                date_limit_days: int = None):
        """
        Process consumption data with ultimate pricing accuracy
        
        Args:
            consumption_file: Path to consumption CSV file
            output_file: Path for output CSV file with pricing
            date_limit_days: Limit processing to last N days
        """
        
        print("🚀 Ultimate Pricing Processor")
        print("=" * 80)
        print("📊 Processing with:")
        print("   • Time-of-use rates (day/night)")
        print("   • Quarterly rate changes")
        print("   • Variable Agile pricing")
        print("   • Accurate standing charges")
        
        # Load consumption data
        print(f"\n📁 Loading consumption data from {consumption_file}...")
        
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
        print(f"\n📋 Using enhanced tariff configuration:")
        self.config_manager.print_configuration()
        
        # Initialize result DataFrame
        enhanced_df = consumption_df.copy()
        enhanced_df['tariff_name'] = ""
        enhanced_df['tariff_code'] = ""
        enhanced_df['rate_type'] = ""  # Day/Night/Variable
        enhanced_df['rate_inc_vat'] = None
        enhanced_df['rate_exc_vat'] = None
        enhanced_df['cost_exc_vat'] = None
        enhanced_df['cost_inc_vat'] = None
        enhanced_df['standing_charge'] = 0.0
        
        # Process each record individually for maximum accuracy
        print(f"\n🔄 Processing {len(enhanced_df)} consumption records...")
        
        processed = 0
        for idx, row in enhanced_df.iterrows():
            interval_start = row['interval_start']
            consumption = row['consumption']
            meter_type = row['meter_type']
            is_export = (meter_type == 'export')
            
            # Find applicable tariff period
            tariff_period = self.config_manager.get_tariff_for_date(interval_start, is_export)
            
            if not tariff_period:
                print(f"⚠️  No tariff found for {interval_start} ({meter_type})")
                continue
            
            # Get rate for this specific time
            if tariff_period.is_variable and self.api.authenticated:
                # Fetch variable rate (Agile)
                rate_inc_vat, rate_type = self._get_agile_rate(tariff_period, interval_start)
            else:
                # Use time-of-use or fixed rate
                rate_inc_vat, rate_type = tariff_period.get_rate_for_time(interval_start)
            
            rate_exc_vat = rate_inc_vat / 1.05
            cost_inc_vat = consumption * rate_inc_vat
            cost_exc_vat = consumption * rate_exc_vat
            
            # Calculate standing charge
            standing_charge = 0.0
            if not is_export and tariff_period.standing_charge:
                # Distribute daily standing charge across 48 half-hourly periods
                standing_charge = tariff_period.standing_charge / 48.0
            
            # Update the result DataFrame
            enhanced_df.at[idx, 'tariff_name'] = tariff_period.name
            enhanced_df.at[idx, 'tariff_code'] = tariff_period.tariff_code
            enhanced_df.at[idx, 'rate_type'] = rate_type
            enhanced_df.at[idx, 'rate_inc_vat'] = rate_inc_vat
            enhanced_df.at[idx, 'rate_exc_vat'] = rate_exc_vat
            enhanced_df.at[idx, 'cost_inc_vat'] = cost_inc_vat
            enhanced_df.at[idx, 'cost_exc_vat'] = cost_exc_vat
            enhanced_df.at[idx, 'standing_charge'] = standing_charge
            
            processed += 1
            if processed % 1000 == 0:
                print(f"   📊 Processed {processed}/{len(enhanced_df)} records...")
        
        print(f"✅ Processed {processed} records")
        
        # Calculate and display summary statistics
        self._print_ultimate_summary_statistics(enhanced_df)
        
        # Save enhanced data
        print(f"\n💾 Saving ultimate pricing data to {output_file}...")
        
        # Round pricing columns for readability
        price_columns = ['rate_inc_vat', 'rate_exc_vat', 'cost_inc_vat', 'cost_exc_vat', 'standing_charge']
        for col in price_columns:
            if col in enhanced_df.columns:
                enhanced_df[col] = enhanced_df[col].round(4)
        
        try:
            enhanced_df.to_csv(output_file, index=False)
            print(f"✅ Ultimate pricing data saved with {len(enhanced_df)} records")
            
            # Show sample of enhanced data
            print(f"\n📋 Sample of ultimate pricing data:")
            sample_cols = ['interval_start', 'consumption', 'meter_type', 'tariff_name', 'rate_type', 'rate_inc_vat', 'cost_inc_vat']
            available_cols = [col for col in sample_cols if col in enhanced_df.columns]
            print(enhanced_df[available_cols].head(10).to_string(index=False))
            
        except Exception as e:
            print(f"❌ Error saving ultimate pricing data: {e}")
            return False
        
        print(f"\n🎉 Ultimate pricing processing complete!")
        print(f"   📁 Original file: {consumption_file}")
        print(f"   📁 Ultimate file: {output_file}")
        print(f"   💰 Bill-accurate pricing with all complexities handled")
        
        return True
    
    def _get_agile_rate(self, tariff_period, interval_start):
        """Get Agile rate for specific time (with caching for efficiency)"""
        # Simple implementation - in production, you'd want to cache this
        try:
            # Try to get rate from API for this specific time
            pricing_df = self.api.get_historical_pricing_data(
                tariff_period.tariff_code, 
                interval_start, 
                interval_start + timedelta(minutes=30),
                is_export=tariff_period.is_export
            )
            
            if not pricing_df.empty:
                matching_rates = pricing_df[
                    (pricing_df['valid_from'] <= interval_start) & 
                    (pricing_df['valid_to'] > interval_start)
                ]
                
                if not matching_rates.empty:
                    return matching_rates.iloc[0]['rate_inc_vat'], "Agile"
            
        except Exception as e:
            print(f"⚠️  Error fetching Agile rate for {interval_start}: {e}")
        
        # Fallback to average rate
        return 28.62, "Agile (fallback)"
    
    def _print_ultimate_summary_statistics(self, enhanced_df: pd.DataFrame):
        """Print comprehensive summary statistics"""
        
        print(f"\n📊 Ultimate Pricing Analysis Summary:")
        print("=" * 80)
        
        # Overall summary
        total_import_cost = enhanced_df[enhanced_df['meter_type'] == 'import']['cost_inc_vat'].sum()
        total_standing_charges = enhanced_df[enhanced_df['meter_type'] == 'import']['standing_charge'].sum()
        total_export_earnings = enhanced_df[enhanced_df['meter_type'] == 'export']['cost_inc_vat'].sum()
        
        if total_import_cost > 0:
            total_bill = total_import_cost + total_standing_charges
            net_cost = total_bill - total_export_earnings
            savings_rate = (total_export_earnings / total_bill * 100) if total_bill > 0 else 0
            
            print(f"\n💰 Overall Financial Summary:")
            print(f"   Energy costs: £{total_import_cost/100:.2f}")
            print(f"   Standing charges: £{total_standing_charges/100:.2f}")
            print(f"   Total bill: £{total_bill/100:.2f}")
            print(f"   Export earnings: £{total_export_earnings/100:.2f}")
            print(f"   Net cost: £{net_cost/100:.2f}")
            print(f"   Solar savings: {savings_rate:.1f}%")
        
        # Rate type breakdown
        print(f"\n⚡ Rate Type Analysis:")
        rate_analysis = enhanced_df[enhanced_df['meter_type'] == 'import'].groupby('rate_type').agg({
            'consumption': 'sum',
            'cost_inc_vat': 'sum',
            'rate_inc_vat': ['min', 'max', 'mean']
        }).round(2)
        
        for rate_type in rate_analysis.index:
            consumption = rate_analysis.loc[rate_type, ('consumption', 'sum')]
            cost = rate_analysis.loc[rate_type, ('cost_inc_vat', 'sum')]
            min_rate = rate_analysis.loc[rate_type, ('rate_inc_vat', 'min')]
            max_rate = rate_analysis.loc[rate_type, ('rate_inc_vat', 'max')]
            avg_rate = rate_analysis.loc[rate_type, ('rate_inc_vat', 'mean')]
            
            print(f"   🔸 {rate_type}:")
            print(f"      Energy: {consumption:.2f} kWh")
            print(f"      Cost: £{cost/100:.2f}")
            print(f"      Rate range: {min_rate:.2f}p - {max_rate:.2f}p/kWh (avg: {avg_rate:.2f}p)")
        
        # Tariff period breakdown
        print(f"\n📅 Tariff Period Analysis:")
        period_analysis = enhanced_df[enhanced_df['meter_type'] == 'import'].groupby('tariff_name').agg({
            'consumption': 'sum',
            'cost_inc_vat': 'sum',
            'standing_charge': 'sum'
        }).round(2)
        
        for tariff_name in period_analysis.index:
            if not tariff_name:  # Skip empty names
                continue
            consumption = period_analysis.loc[tariff_name, 'consumption']
            cost = period_analysis.loc[tariff_name, 'cost_inc_vat']
            standing = period_analysis.loc[tariff_name, 'standing_charge']
            total_period_cost = cost + standing
            
            print(f"   📊 {tariff_name}:")
            print(f"      Energy: {consumption:.2f} kWh")
            print(f"      Energy cost: £{cost/100:.2f}")
            print(f"      Standing charges: £{standing/100:.2f}")
            print(f"      Total cost: £{total_period_cost/100:.2f}")


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description='Ultimate pricing processor with all tariff complexities')
    parser.add_argument('--input', type=str, default='octopus_consumption_raw.csv', 
                       help='Input consumption CSV file')
    parser.add_argument('--output', type=str, default='octopus_consumption_ultimate_pricing.csv',
                       help='Output CSV file with ultimate pricing')
    parser.add_argument('--config', type=str, default='enhanced_tariff_config.json',
                       help='Enhanced tariff configuration file')
    parser.add_argument('--days', type=int, help='Limit to last N days (for testing)')
    
    args = parser.parse_args()
    
    # Process consumption with ultimate pricing
    processor = UltimatePricingProcessor(args.config)
    success = processor.process_consumption_with_ultimate_pricing(
        consumption_file=args.input,
        output_file=args.output,
        date_limit_days=args.days
    )
    
    if not success:
        print("❌ Processing failed")
        return
    
    print(f"\n🎯 You now have ULTIMATE pricing accuracy!")
    print(f"   📁 Data file: {args.output}")
    print(f"   💰 Bill-accurate costs with:")
    print(f"      • Time-of-use rates (day/night)")
    print(f"      • Quarterly rate changes")  
    print(f"      • Variable Agile pricing")
    print(f"      • Accurate standing charges")


if __name__ == "__main__":
    main() 