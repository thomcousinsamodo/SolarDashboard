#!/usr/bin/env python3
"""
Octopus Energy Lifetime Data Fetcher
Enhanced version to fetch historical data with custom date ranges and progress tracking
"""

import requests
import json
import pandas as pd
import database_utils
from credential_manager import CredentialManager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import time
from dataclasses import dataclass
import argparse
from tqdm import tqdm


@dataclass
class MeterInfo:
    """Data class to store meter information"""
    mpan: str
    serial_number: str
    is_export: bool


class OctopusEnergyLifetimeAPI:
    """Enhanced class to interact with Octopus Energy API for lifetime data"""
    
    def __init__(self, api_key: str):
        """
        Initialize the API client
        
        Args:
            api_key: Your Octopus Energy API key
        """
        self.api_key = api_key
        self.base_url = "https://api.octopus.energy/v1"
        self.session = requests.Session()
        self.session.auth = (api_key, '')
        
    def get_account_info(self, account_number: str) -> Dict:
        """Get account information including meter details"""
        url = f"{self.base_url}/accounts/{account_number}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching account info: {e}")
            return {}
    
    def extract_meter_info(self, account_data: Dict) -> List[MeterInfo]:
        """Extract meter information from account data"""
        meters = []
        
        for property_info in account_data.get('properties', []):
            for meter_point in property_info.get('electricity_meter_points', []):
                mpan = meter_point.get('mpan')
                is_export = meter_point.get('is_export', False)
                
                for meter in meter_point.get('meters', []):
                    serial_number = meter.get('serial_number')
                    if mpan and serial_number:
                        meters.append(MeterInfo(
                            mpan=mpan,
                            serial_number=serial_number,
                            is_export=is_export
                        ))
        
        return meters
    
    def get_consumption_data_chunked(self, mpan: str, serial_number: str, 
                                   start_date: datetime, end_date: datetime,
                                   chunk_days: int = 90, delay_seconds: float = 0.5) -> List[Dict]:
        """
        Get consumption data in chunks to handle large date ranges
        
        Args:
            mpan: Meter Point Administration Number
            serial_number: Meter serial number
            start_date: Start date (datetime object)
            end_date: End date (datetime object)
            chunk_days: Number of days per chunk (default 90)
            delay_seconds: Delay between API calls (default 0.5s)
            
        Returns:
            List of consumption records
        """
        all_results = []
        current_date = start_date
        
        # Calculate total chunks for progress bar
        total_days = (end_date - start_date).days
        total_chunks = (total_days // chunk_days) + (1 if total_days % chunk_days > 0 else 0)
        
        print(f"Fetching data in {total_chunks} chunks of {chunk_days} days each...")
        
        with tqdm(total=total_chunks, desc="Fetching chunks") as pbar:
            while current_date < end_date:
                chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
                
                period_from = current_date.strftime('%Y-%m-%dT00:00:00Z')
                period_to = chunk_end.strftime('%Y-%m-%dT23:59:59Z')
                
                chunk_data = self.get_consumption_data_single_request(
                    mpan, serial_number, period_from, period_to
                )
                
                if chunk_data:
                    all_results.extend(chunk_data)
                
                # Update progress
                pbar.set_postfix({
                    'Current': current_date.strftime('%Y-%m-%d'),
                    'Records': len(all_results)
                })
                pbar.update(1)
                
                current_date = chunk_end
                
                # Rate limiting
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
        
        return all_results
    
    def get_consumption_data_single_request(self, mpan: str, serial_number: str, 
                                          period_from: str, period_to: str,
                                          page_size: int = 25000) -> List[Dict]:
        """
        Get consumption data for a single time period with pagination
        """
        url = f"{self.base_url}/electricity-meter-points/{mpan}/meters/{serial_number}/consumption/"
        
        params = {
            'period_from': period_from,
            'period_to': period_to,
            'page_size': page_size,
            'order_by': 'period'
        }
        
        all_results = []
        
        try:
            while url:
                response = self.session.get(url, params=params if url == f"{self.base_url}/electricity-meter-points/{mpan}/meters/{serial_number}/consumption/" else None)
                response.raise_for_status()
                data = response.json()
                
                all_results.extend(data.get('results', []))
                
                # Check if there's a next page
                url = data.get('next')
                params = None  # Clear params for subsequent requests
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching consumption data: {e}")
            
        return all_results


class EnhancedDataAnalyzer:
    """Enhanced class to analyze large energy consumption datasets"""
    
    @staticmethod
    def to_dataframe(consumption_data: List[Dict], meter_type: str = "import") -> pd.DataFrame:
        """Convert consumption data to pandas DataFrame"""
        if not consumption_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(consumption_data)
        
        # Convert timestamps to datetime with UTC handling
        df['interval_start'] = pd.to_datetime(df['interval_start'], utc=True)
        df['interval_end'] = pd.to_datetime(df['interval_end'], utc=True)
        
        # Add meter type
        df['meter_type'] = meter_type
        
        # Sort by interval start
        df = df.sort_values('interval_start').reset_index(drop=True)
        
        return df
    
    @staticmethod
    def create_comprehensive_summaries(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create multiple summary levels for large datasets"""
        summaries = {}
        
        if df.empty:
            return summaries
        
        # Convert to local timezone (UK) with better handling
        df_local = df.copy()
        
        # Ensure interval_start is datetime and handle timezone conversion safely
        df_local['interval_start'] = pd.to_datetime(df_local['interval_start'], utc=True)
        
        # Convert to UK timezone
        df_local['datetime_local'] = df_local['interval_start'].dt.tz_convert('Europe/London')
        df_local['date'] = df_local['datetime_local'].dt.date
        df_local['year_month'] = df_local['datetime_local'].dt.to_period('M')
        df_local['year'] = df_local['datetime_local'].dt.year
        df_local['hour'] = df_local['datetime_local'].dt.hour
        df_local['day_of_week'] = df_local['datetime_local'].dt.day_name()
        
        # Daily summary
        daily_summary = df_local.groupby(['date', 'meter_type']).agg({
            'consumption': ['sum', 'mean', 'min', 'max', 'count']
        }).round(3)
        daily_summary.columns = ['total_kwh', 'avg_kwh', 'min_kwh', 'max_kwh', 'readings_count']
        daily_summary.reset_index(inplace=True)
        summaries['daily'] = daily_summary
        
        # Monthly summary
        monthly_summary = df_local.groupby(['year_month', 'meter_type']).agg({
            'consumption': ['sum', 'mean', 'count']
        }).round(3)
        monthly_summary.columns = ['total_kwh', 'avg_kwh', 'readings_count']
        monthly_summary.reset_index(inplace=True)
        summaries['monthly'] = monthly_summary
        
        # Yearly summary
        yearly_summary = df_local.groupby(['year', 'meter_type']).agg({
            'consumption': ['sum', 'mean', 'count']
        }).round(3)
        yearly_summary.columns = ['total_kwh', 'avg_kwh', 'readings_count']
        yearly_summary.reset_index(inplace=True)
        summaries['yearly'] = yearly_summary
        
        # Hourly patterns (average by hour across all days)
        hourly_pattern = df_local.groupby(['hour', 'meter_type']).agg({
            'consumption': ['mean', 'count']
        }).round(3)
        hourly_pattern.columns = ['avg_kwh', 'readings_count']
        hourly_pattern.reset_index(inplace=True)
        summaries['hourly_pattern'] = hourly_pattern
        
        # Day of week patterns
        dow_pattern = df_local.groupby(['day_of_week', 'meter_type']).agg({
            'consumption': ['mean', 'sum', 'count']
        }).round(3)
        dow_pattern.columns = ['avg_kwh', 'total_kwh', 'readings_count']
        dow_pattern.reset_index(inplace=True)
        summaries['day_of_week_pattern'] = dow_pattern
        
        return summaries
    
    @staticmethod
    def create_basic_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Create basic daily summary as fallback when timezone conversion fails"""
        if df.empty:
            return pd.DataFrame()
        
        # Simple approach without timezone conversion
        df_local = df.copy()
        df_local['date'] = df_local['interval_start'].dt.date
        
        daily_summary = df_local.groupby(['date', 'meter_type']).agg({
            'consumption': ['sum', 'mean', 'min', 'max', 'count']
        }).round(3)
        daily_summary.columns = ['total_kwh', 'avg_kwh', 'min_kwh', 'max_kwh', 'readings_count']
        daily_summary.reset_index(inplace=True)
        
        return daily_summary


def parse_date(date_string: str) -> datetime:
    """Parse date string in various formats"""
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_string}")


def main():
    """Main function with command line argument support"""
    parser = argparse.ArgumentParser(description='Fetch Octopus Energy consumption data with custom date ranges')
    parser.add_argument('--days', type=int, help='Number of days to fetch (from today backwards)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD format)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD format)')
    parser.add_argument('--lifetime', action='store_true', help='Fetch all available data (may take a while)')
    parser.add_argument('--chunk-days', type=int, default=90, help='Number of days per API request chunk (default: 90)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API calls in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    # Load credentials using secure credential manager
    credential_manager = CredentialManager()
    API_KEY, ACCOUNT_NUMBER = credential_manager.get_credentials()
    
    if not API_KEY or not ACCOUNT_NUMBER:
        print("❌ API credentials not found.")
        print("🔐 Please run credential_manager.py to set up secure credentials:")
        print("   python credential_manager.py")
        return
    
    # Determine date range
    end_date = datetime.now()
    
    if args.lifetime:
        # Start from a reasonable date (most smart meters installed after 2015)
        start_date = datetime(2015, 1, 1)
        print("🔄 Fetching lifetime data (from 2015-01-01 to now)")
    elif args.days:
        start_date = end_date - timedelta(days=args.days)
        print(f"🔄 Fetching last {args.days} days of data")
    elif args.start_date and args.end_date:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
        print(f"🔄 Fetching data from {start_date.date()} to {end_date.date()}")
    elif args.start_date:
        start_date = parse_date(args.start_date)
        print(f"🔄 Fetching data from {start_date.date()} to {end_date.date()}")
    else:
        # Default to last 365 days
        start_date = end_date - timedelta(days=365)
        print(f"🔄 No date range specified, fetching last 365 days")
    
    print(f"📅 Date range: {start_date.date()} to {end_date.date()}")
    print(f"📊 Total days: {(end_date - start_date).days}")
    
    # Initialize API client
    api = OctopusEnergyLifetimeAPI(API_KEY)
    analyzer = EnhancedDataAnalyzer()
    
    print("\n🔍 Fetching account information...")
    account_data = api.get_account_info(ACCOUNT_NUMBER)
    
    if not account_data:
        print("❌ Failed to fetch account data. Please check your API key and account number.")
        return
    
    # Extract meter information
    meters = api.extract_meter_info(account_data)
    
    if not meters:
        print("❌ No meters found in account data.")
        return
    
    print(f"✅ Found {len(meters)} meter(s):")
    for i, meter in enumerate(meters):
        meter_type = "Export" if meter.is_export else "Import"
        print(f"  {i+1}. MPAN: {meter.mpan}, Serial: {meter.serial_number}, Type: {meter_type}")
    
    all_data = []
    
    # Fetch data for each meter
    for meter in meters:
        meter_type = "export" if meter.is_export else "import"
        print(f"\n🔽 Fetching {meter_type} data for MPAN: {meter.mpan}")
        
        consumption_data = api.get_consumption_data_chunked(
            meter.mpan, 
            meter.serial_number, 
            start_date,
            end_date,
            chunk_days=args.chunk_days,
            delay_seconds=args.delay
        )
        
        if consumption_data:
            df = analyzer.to_dataframe(consumption_data, meter_type)
            all_data.append(df)
            print(f"✅ Retrieved {len(consumption_data):,} readings")
            
            if not df.empty:
                total_consumption = df['consumption'].sum()
                date_range = f"{df['interval_start'].min().date()} to {df['interval_start'].max().date()}"
                print(f"  📊 Total consumption: {total_consumption:.3f} kWh")
                print(f"  📅 Actual date range: {date_range}")
        else:
            print(f"❌ No data available for this meter")
    
    if all_data:
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        print("\n" + "="*80)
        print("📈 ANALYSIS SUMMARY")
        print("="*80)
        
        # Create comprehensive summaries with error handling
        try:
            summaries = analyzer.create_comprehensive_summaries(combined_df)
        except Exception as e:
            print(f"⚠️  Warning: Could not create all summaries due to data format issues: {e}")
            print("📊 Creating basic summaries instead...")
            summaries = {'daily': analyzer.create_basic_daily_summary(combined_df)}
        
        # Display summaries
        for summary_type, summary_df in summaries.items():
            if not summary_df.empty:
                print(f"\n{summary_type.upper().replace('_', ' ')} SUMMARY:")
                if summary_type in ['daily', 'monthly', 'yearly']:
                    print(summary_df.tail(10).to_string(index=False))
                else:
                    print(summary_df.to_string(index=False))
        
        # Save data to CSV files with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"\n💾 Saving data to CSV files (timestamp: {timestamp})...")
        
        # Save raw data to database
        print("💾 Saving raw data to database...")
        if database_utils.save_consumption_data(combined_df, "consumption_raw"):
            print("✅ Raw data saved to database successfully")
            
            # Create daily and monthly aggregates from raw data
            print("Creating daily aggregates...")
            database_utils.create_daily_aggregates()
            print("Creating monthly aggregates...")
            database_utils.create_monthly_aggregates()
            print("✅ Aggregates created successfully")
        else:
            print("❌ Failed to save raw data to database")
            
        # Optional: Save timestamped backup to CSV
        raw_filename = f'octopus_consumption_raw_{timestamp}.csv'
        combined_df.to_csv(f'data/csv_backup/{raw_filename}', index=False)
        print(f"✅ Backup saved to: data/csv_backup/{raw_filename}")
        
        # Save summary backups to CSV (optional)
        for summary_type, summary_df in summaries.items():
            if not summary_df.empty:
                filename = f'octopus_consumption_{summary_type}_{timestamp}.csv'
                summary_df.to_csv(f'data/csv_backup/{filename}', index=False)
                print(f"✅ {summary_type.title()} summary backup saved to: data/csv_backup/{filename}")
        
        # Statistics
        total_records = len(combined_df)
        date_span = (combined_df['interval_start'].max() - combined_df['interval_start'].min()).days
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"  📋 Total records: {total_records:,}")
        print(f"  📅 Date span: {date_span} days")
        print(f"  🔋 Import records: {len(combined_df[combined_df['meter_type'] == 'import']):,}")
        print(f"  ☀️ Export records: {len(combined_df[combined_df['meter_type'] == 'export']):,}")
        
        print(f"\n🌐 Dashboard data updated! Refresh your browser at http://127.0.0.1:8050")
        
    else:
        print("\n❌ No consumption data was retrieved.")


if __name__ == "__main__":
    main() 