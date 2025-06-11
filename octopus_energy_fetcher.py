#!/usr/bin/env python3
"""
Octopus Energy API Data Fetcher
A script to fetch import and export electricity consumption data from Octopus Energy API
and perform basic analysis.
"""

import requests
import json
import pandas as pd
import database_utils
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
from dataclasses import dataclass


@dataclass
class MeterInfo:
    """Data class to store meter information"""
    mpan: str
    serial_number: str
    is_export: bool
    
    
class OctopusEnergyAPI:
    """Class to interact with Octopus Energy API"""
    
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
        """
        Get account information including meter details
        
        Args:
            account_number: Your account number (format: A-AAAA1111)
            
        Returns:
            Dictionary containing account information
        """
        url = f"{self.base_url}/accounts/{account_number}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching account info: {e}")
            return {}
    
    def extract_meter_info(self, account_data: Dict) -> List[MeterInfo]:
        """
        Extract meter information from account data
        
        Args:
            account_data: Account data from API
            
        Returns:
            List of MeterInfo objects
        """
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
    
    def get_consumption_data(self, mpan: str, serial_number: str, 
                           period_from: str, period_to: str,
                           page_size: int = 25000) -> List[Dict]:
        """
        Get consumption data for a specific meter
        
        Args:
            mpan: Meter Point Administration Number
            serial_number: Meter serial number
            period_from: Start date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
            period_to: End date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
            page_size: Number of records per page (max 25000)
            
        Returns:
            List of consumption records
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
                params = None  # Clear params for subsequent requests as they're in the next URL
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching consumption data: {e}")
            
        return all_results


class DataAnalyzer:
    """Class to analyze energy consumption data"""
    
    @staticmethod
    def to_dataframe(consumption_data: List[Dict], meter_type: str = "import") -> pd.DataFrame:
        """
        Convert consumption data to pandas DataFrame
        
        Args:
            consumption_data: List of consumption records from API
            meter_type: Type of meter ("import" or "export")
            
        Returns:
            Pandas DataFrame with processed data
        """
        if not consumption_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(consumption_data)
        
        # Convert timestamps to datetime
        df['interval_start'] = pd.to_datetime(df['interval_start'])
        df['interval_end'] = pd.to_datetime(df['interval_end'])
        
        # Add meter type
        df['meter_type'] = meter_type
        
        # Sort by interval start
        df = df.sort_values('interval_start').reset_index(drop=True)
        
        return df
    
    @staticmethod
    def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create daily summary of consumption
        
        Args:
            df: DataFrame with consumption data
            
        Returns:
            DataFrame with daily totals
        """
        if df.empty:
            return pd.DataFrame()
        
        # Convert to local timezone (UK)
        df_local = df.copy()
        df_local['date'] = df_local['interval_start'].dt.tz_convert('Europe/London').dt.date
        
        daily_summary = df_local.groupby(['date', 'meter_type']).agg({
            'consumption': ['sum', 'mean', 'min', 'max', 'count']
        }).round(3)
        
        # Flatten column names
        daily_summary.columns = ['total_kwh', 'avg_kwh', 'min_kwh', 'max_kwh', 'readings_count']
        daily_summary.reset_index(inplace=True)
        
        return daily_summary
    
    @staticmethod
    def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create monthly summary of consumption
        
        Args:
            df: DataFrame with consumption data
            
        Returns:
            DataFrame with monthly totals
        """
        if df.empty:
            return pd.DataFrame()
        
        # Convert to local timezone (UK)
        df_local = df.copy()
        df_local['year_month'] = df_local['interval_start'].dt.tz_convert('Europe/London').dt.to_period('M')
        
        monthly_summary = df_local.groupby(['year_month', 'meter_type']).agg({
            'consumption': ['sum', 'mean', 'count']
        }).round(3)
        
        # Flatten column names
        monthly_summary.columns = ['total_kwh', 'avg_kwh', 'readings_count']
        monthly_summary.reset_index(inplace=True)
        
        return monthly_summary


def main():
    """Main function to demonstrate the API usage"""
    
    # Configuration - you'll need to set these
    API_KEY = os.getenv('OCTOPUS_API_KEY', 'your_api_key_here')
    ACCOUNT_NUMBER = os.getenv('OCTOPUS_ACCOUNT_NUMBER', 'A-AAAA1111')
    
    if API_KEY == 'your_api_key_here' or ACCOUNT_NUMBER == 'A-AAAA1111':
        print("Please set your API key and account number in environment variables:")
        print("export OCTOPUS_API_KEY='your_actual_api_key'")
        print("export OCTOPUS_ACCOUNT_NUMBER='your_actual_account_number'")
        print("\nOr modify the script to include them directly (less secure)")
        return
    
    # Initialize API client
    api = OctopusEnergyAPI(API_KEY)
    analyzer = DataAnalyzer()
    
    print("Fetching account information...")
    account_data = api.get_account_info(ACCOUNT_NUMBER)
    
    if not account_data:
        print("Failed to fetch account data. Please check your API key and account number.")
        return
    
    # Extract meter information
    meters = api.extract_meter_info(account_data)
    
    if not meters:
        print("No meters found in account data.")
        return
    
    print(f"Found {len(meters)} meter(s):")
    for i, meter in enumerate(meters):
        meter_type = "Export" if meter.is_export else "Import"
        print(f"  {i+1}. MPAN: {meter.mpan}, Serial: {meter.serial_number}, Type: {meter_type}")
    
    # Set date range for data collection (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    period_from = start_date.strftime('%Y-%m-%dT00:00:00Z')
    period_to = end_date.strftime('%Y-%m-%dT23:59:59Z')
    
    print(f"\nFetching consumption data from {start_date.date()} to {end_date.date()}...")
    
    all_data = []
    
    # Fetch data for each meter
    for meter in meters:
        meter_type = "export" if meter.is_export else "import"
        print(f"\nFetching {meter_type} data for MPAN: {meter.mpan}")
        
        consumption_data = api.get_consumption_data(
            meter.mpan, 
            meter.serial_number, 
            period_from, 
            period_to
        )
        
        if consumption_data:
            df = analyzer.to_dataframe(consumption_data, meter_type)
            all_data.append(df)
            print(f"  Retrieved {len(consumption_data)} readings")
            
            # Show basic statistics
            if not df.empty:
                total_consumption = df['consumption'].sum()
                avg_consumption = df['consumption'].mean()
                print(f"  Total consumption: {total_consumption:.3f} kWh")
                print(f"  Average per reading: {avg_consumption:.3f} kWh")
        else:
            print(f"  No data available for this meter")
    
    if all_data:
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        print("\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        
        # Daily summary
        daily_summary = analyzer.daily_summary(combined_df)
        if not daily_summary.empty:
            print("\nDAILY SUMMARY (Last 10 days):")
            print(daily_summary.tail(10).to_string(index=False))
        
        # Monthly summary
        monthly_summary = analyzer.monthly_summary(combined_df)
        if not monthly_summary.empty:
            print("\nMONTHLY SUMMARY:")
            print(monthly_summary.to_string(index=False))
        
        # Save data to database
        print("\n💾 Saving data to database...")
        
        # Save raw data to database
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
            
        # Optional: Save backups to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        combined_df.to_csv(f'data/csv_backup/octopus_consumption_raw_{timestamp}.csv', index=False)
        print(f"✅ Backup saved to: data/csv_backup/octopus_consumption_raw_{timestamp}.csv")
    
    else:
        print("\nNo consumption data was retrieved.")


if __name__ == "__main__":
    main() 