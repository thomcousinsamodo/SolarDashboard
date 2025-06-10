#!/usr/bin/env python3
"""
Comprehensive Data Processor
Creates a single enriched dataset with consumption and precise cost calculations
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import json
import pytz
from pathlib import Path
import os
from typing import Dict, List, Optional


class ComprehensiveDataProcessor:
    """Process raw consumption data into enriched dataset with precise pricing."""
    
    def __init__(self, tariff_config_file: str = 'flexible_tariff_config.json'):
        self.tariff_config_file = tariff_config_file
        self.tariff_periods = []
        self.uk_tz = pytz.timezone('Europe/London')
        self.load_tariff_configuration()
    
    def load_tariff_configuration(self):
        """Load tariff configuration from JSON file."""
        try:
            with open(self.tariff_config_file, 'r') as f:
                config = json.load(f)
            
            self.account_number = config.get('account_number', 'A-AFDADE77')
            self.tariff_periods = config.get('tariff_periods', [])
            
            print(f"✅ Loaded {len(self.tariff_periods)} tariff periods")
            print(f"📅 Coverage: {self.tariff_periods[0]['start_date']} to {self.tariff_periods[-1]['end_date']}")
            
        except Exception as e:
            print(f"❌ Error loading tariff configuration: {e}")
            self.tariff_periods = []
    
    def find_tariff_period(self, timestamp: datetime) -> Optional[Dict]:
        """Find the appropriate tariff period for a given timestamp."""
        date_str = timestamp.strftime('%Y-%m-%d')
        
        for period in self.tariff_periods:
            if period['start_date'] <= date_str <= period['end_date']:
                return period
        
        return None
    
    def get_precise_rate_for_timestamp(self, timestamp: datetime, tariff_period: Dict) -> tuple:
        """Get the precise rate for a specific timestamp."""
        # Convert to UK timezone if needed
        if timestamp.tzinfo is None:
            uk_timestamp = self.uk_tz.localize(timestamp)
        elif timestamp.tzinfo != self.uk_tz:
            uk_timestamp = timestamp.astimezone(self.uk_tz)
        else:
            uk_timestamp = timestamp
        
        time_only = uk_timestamp.time()
        
        if tariff_period['rate_type'] == 'time_of_use':
            # Find the applicable time-of-use rate
            for rate in tariff_period['time_of_use_rates']:
                start_time = datetime.strptime(rate['start_time'], '%H:%M').time()
                end_time = datetime.strptime(rate['end_time'], '%H:%M').time()
                
                # Handle time ranges that cross midnight
                if start_time <= end_time:
                    # Normal range (e.g., 07:00-23:00)
                    if start_time <= time_only < end_time:
                        return rate['rate_pence_per_kwh'], rate['rate_name']
                else:
                    # Range crosses midnight (e.g., 23:00-07:00)
                    if time_only >= start_time or time_only < end_time:
                        return rate['rate_pence_per_kwh'], rate['rate_name']
            
            # Fallback to first rate if no match
            first_rate = tariff_period['time_of_use_rates'][0]
            return first_rate['rate_pence_per_kwh'], first_rate['rate_name']
        
        else:
            # Fixed rate
            return tariff_period['rate_pence_per_kwh'], 'Fixed'
    
    def process_raw_consumption_data(self, 
                                   input_file: str = 'octopus_consumption_raw.csv',
                                   output_file: str = 'octopus_consumption_enriched.csv') -> bool:
        """Process raw consumption data into enriched dataset with precise pricing."""
        
        print("🚀 COMPREHENSIVE DATA PROCESSOR")
        print("=" * 60)
        
        # Load raw consumption data
        print(f"📁 Loading raw consumption data from {input_file}...")
        
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            return False
        
        try:
            raw_df = pd.read_csv(input_file)
            print(f"✅ Loaded {len(raw_df)} consumption records")
            
            # Convert timestamps
            raw_df['interval_start'] = pd.to_datetime(raw_df['interval_start'], utc=True)
            raw_df['interval_end'] = pd.to_datetime(raw_df['interval_end'], utc=True)
            
            # Get date range
            start_date = raw_df['interval_start'].min()
            end_date = raw_df['interval_start'].max()
            print(f"📅 Data range: {start_date.date()} to {end_date.date()}")
            
        except Exception as e:
            print(f"❌ Error loading consumption data: {e}")
            return False
        
        if raw_df.empty:
            print("❌ No consumption data to process")
            return False
        
        # Create enriched dataset
        print(f"\n💰 Enriching data with precise pricing...")
        enriched_df = raw_df.copy()
        
        # Add pricing columns
        enriched_df['tariff_code'] = ''
        enriched_df['tariff_period'] = ''
        enriched_df['rate_pence_per_kwh'] = 0.0
        enriched_df['rate_type'] = ''
        enriched_df['cost_pence'] = 0.0
        enriched_df['cost_pounds'] = 0.0
        enriched_df['standing_charge_pence'] = 0.0
        enriched_df['standing_charge_pounds'] = 0.0
        enriched_df['total_cost_pence'] = 0.0
        enriched_df['total_cost_pounds'] = 0.0
        
        # Process each record individually for maximum accuracy
        processed_count = 0
        total_records = len(enriched_df)
        
        for index, row in enriched_df.iterrows():
            interval_start = row['interval_start']
            consumption = row['consumption']
            meter_type = row['meter_type']
            
            # Find applicable tariff period
            tariff_period = self.find_tariff_period(interval_start)
            
            if tariff_period is None:
                continue
            
            # Get precise rate for this timestamp
            rate_pence_per_kwh, rate_type = self.get_precise_rate_for_timestamp(interval_start, tariff_period)
            
            # Calculate costs
            cost_pence = consumption * rate_pence_per_kwh
            cost_pounds = cost_pence / 100
            
            # Calculate standing charge (only for import, distributed across 48 half-hourly periods per day)
            standing_charge_pence = 0.0
            standing_charge_pounds = 0.0
            if meter_type == 'import':
                standing_charge_pence = tariff_period['standing_charge_pence_per_day'] / 48.0
                standing_charge_pounds = standing_charge_pence / 100
            
            # Total costs
            total_cost_pence = cost_pence + standing_charge_pence
            total_cost_pounds = total_cost_pence / 100
            
            # Update the record
            enriched_df.at[index, 'tariff_code'] = tariff_period['tariff_code']
            enriched_df.at[index, 'tariff_period'] = f"{tariff_period['start_date']} to {tariff_period['end_date']}"
            enriched_df.at[index, 'rate_pence_per_kwh'] = rate_pence_per_kwh
            enriched_df.at[index, 'rate_type'] = rate_type
            enriched_df.at[index, 'cost_pence'] = cost_pence
            enriched_df.at[index, 'cost_pounds'] = cost_pounds
            enriched_df.at[index, 'standing_charge_pence'] = standing_charge_pence
            enriched_df.at[index, 'standing_charge_pounds'] = standing_charge_pounds
            enriched_df.at[index, 'total_cost_pence'] = total_cost_pence
            enriched_df.at[index, 'total_cost_pounds'] = total_cost_pounds
            
            processed_count += 1
            
            # Progress update
            if processed_count % 5000 == 0:
                progress = (processed_count / total_records) * 100
                print(f"   📊 Processed {processed_count:,}/{total_records:,} records ({progress:.1f}%)")
        
        print(f"✅ Processed {processed_count:,} records with precise pricing")
        
        # Calculate and display summary statistics
        self._print_enriched_summary_statistics(enriched_df)
        
        # Save enriched dataset
        print(f"\n💾 Saving enriched dataset to {output_file}...")
        
        try:
            # Round monetary columns for readability
            money_columns = ['rate_pence_per_kwh', 'cost_pence', 'cost_pounds', 
                           'standing_charge_pence', 'standing_charge_pounds',
                           'total_cost_pence', 'total_cost_pounds']
            
            for col in money_columns:
                if col in enriched_df.columns:
                    enriched_df[col] = enriched_df[col].round(4)
            
            enriched_df.to_csv(output_file, index=False)
            print(f"✅ Enriched dataset saved with {len(enriched_df):,} records")
            
            # Show sample of enriched data
            print(f"\n📋 Sample of enriched data:")
            sample_cols = ['interval_start', 'consumption', 'meter_type', 'tariff_code', 
                          'rate_type', 'rate_pence_per_kwh', 'cost_pounds', 'total_cost_pounds']
            available_cols = [col for col in sample_cols if col in enriched_df.columns]
            print(enriched_df[available_cols].head(10).to_string(index=False))
            
        except Exception as e:
            print(f"❌ Error saving enriched dataset: {e}")
            return False
        
        print(f"\n🎉 Comprehensive data processing complete!")
        print(f"   📁 Input file: {input_file}")
        print(f"   📁 Output file: {output_file}")
        print(f"   💰 Precise half-hourly pricing with bill-accurate tariff data")
        print(f"   📊 {processed_count:,} records enriched")
        
        return True
    
    def create_daily_summary(self, 
                           input_file: str = 'octopus_consumption_enriched.csv',
                           output_file: str = 'octopus_consumption_daily_enriched.csv') -> bool:
        """Create daily summary from enriched half-hourly data."""
        
        print(f"\n📊 Creating daily summary from enriched data...")
        
        if not os.path.exists(input_file):
            print(f"❌ Enriched file not found: {input_file}")
            return False
        
        try:
            enriched_df = pd.read_csv(input_file)
            enriched_df['interval_start'] = pd.to_datetime(enriched_df['interval_start'], utc=True)
            
            # Convert to local timezone for daily grouping
            enriched_df['date_local'] = enriched_df['interval_start'].dt.tz_convert('Europe/London').dt.date
            
            # Group by date and meter type
            daily_summary = enriched_df.groupby(['date_local', 'meter_type']).agg({
                'consumption': ['sum', 'count'],
                'cost_pounds': 'sum',
                'standing_charge_pounds': 'sum',
                'total_cost_pounds': 'sum',
                'rate_pence_per_kwh': ['min', 'max', 'mean'],
                'tariff_code': 'first',
                'rate_type': lambda x: ', '.join([str(i) for i in x.unique() if str(i) != 'nan'])
            }).round(4)
            
            # Flatten column names
            daily_summary.columns = [
                'total_kwh', 'readings_count',
                'cost_pounds', 'standing_charge_pounds', 'total_cost_pounds',
                'min_rate', 'max_rate', 'avg_rate',
                'tariff_code', 'rate_types'
            ]
            
            daily_summary.reset_index(inplace=True)
            daily_summary.rename(columns={'date_local': 'date'}, inplace=True)
            
            # Save daily summary
            daily_summary.to_csv(output_file, index=False)
            print(f"✅ Daily summary saved with {len(daily_summary)} records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating daily summary: {e}")
            return False
    
    def _print_enriched_summary_statistics(self, enriched_df: pd.DataFrame):
        """Print summary statistics for enriched dataset."""
        
        print(f"\n📊 ENRICHED DATA ANALYSIS SUMMARY:")
        print("=" * 60)
        
        # Overall financial summary
        import_data = enriched_df[enriched_df['meter_type'] == 'import']
        export_data = enriched_df[enriched_df['meter_type'] == 'export']
        
        if not import_data.empty:
            total_import_kwh = import_data['consumption'].sum()
            total_import_cost = import_data['cost_pounds'].sum()
            total_standing_charges = import_data['standing_charge_pounds'].sum()
            total_bill = total_import_cost + total_standing_charges
            
            print(f"\n🔴 Import Analysis:")
            print(f"   Energy consumed: {total_import_kwh:,.2f} kWh")
            print(f"   Energy costs: £{total_import_cost:,.2f}")
            print(f"   Standing charges: £{total_standing_charges:,.2f}")
            print(f"   Total bill: £{total_bill:,.2f}")
            
            # Rate analysis
            min_rate = import_data['rate_pence_per_kwh'].min()
            max_rate = import_data['rate_pence_per_kwh'].max()
            avg_rate = (total_import_cost * 100) / total_import_kwh if total_import_kwh > 0 else 0
            
            print(f"   Rate range: {min_rate:.2f}p - {max_rate:.2f}p/kWh")
            print(f"   Weighted avg rate: {avg_rate:.2f}p/kWh")
        
        if not export_data.empty:
            total_export_kwh = export_data['consumption'].sum()
            total_export_earnings = export_data['cost_pounds'].sum()
            avg_export_rate = (total_export_earnings * 100) / total_export_kwh if total_export_kwh > 0 else 0
            
            print(f"\n🟢 Export Analysis:")
            print(f"   Energy exported: {total_export_kwh:,.2f} kWh")
            print(f"   Export earnings: £{total_export_earnings:,.2f}")
            print(f"   Average export rate: {avg_export_rate:.2f}p/kWh")
        
        # Net analysis
        if not import_data.empty and not export_data.empty:
            net_cost = total_bill - total_export_earnings
            savings_rate = (total_export_earnings / total_bill * 100) if total_bill > 0 else 0
            
            print(f"\n💰 Net Analysis:")
            print(f"   Net cost: £{net_cost:,.2f}")
            print(f"   Solar savings: {savings_rate:.1f}%")
        
        # Tariff breakdown
        print(f"\n📅 Tariff Period Breakdown:")
        tariff_analysis = import_data.groupby(['tariff_code', 'rate_type']).agg({
            'consumption': 'sum',
            'cost_pounds': 'sum',
            'rate_pence_per_kwh': 'mean'
        }).round(2)
        
        for (tariff_code, rate_type), data in tariff_analysis.iterrows():
            consumption = data['consumption']
            cost = data['cost_pounds']
            avg_rate = data['rate_pence_per_kwh']
            
            print(f"   📊 {tariff_code} ({rate_type}):")
            print(f"      Energy: {consumption:,.1f} kWh | Cost: £{cost:,.2f} | Avg: {avg_rate:.2f}p/kWh")


def main():
    """Main function to run comprehensive data processing."""
    print("🚀 COMPREHENSIVE DATA PROCESSOR")
    print("Creating enriched dataset with precise half-hourly pricing")
    print("=" * 60)
    
    processor = ComprehensiveDataProcessor()
    
    if not processor.tariff_periods:
        print("❌ No tariff periods loaded - cannot process data")
        return
    
    # Process raw consumption data
    success = processor.process_raw_consumption_data()
    
    if success:
        # Create daily summary
        processor.create_daily_summary()
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Use 'octopus_consumption_enriched.csv' for detailed half-hourly analysis")
        print(f"   2. Use 'octopus_consumption_daily_enriched.csv' for daily summaries")
        print(f"   3. Update dashboard to use enriched data for instant, accurate pricing")
    else:
        print("❌ Processing failed")


if __name__ == '__main__':
    main() 