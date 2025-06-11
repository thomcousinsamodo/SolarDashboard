#!/usr/bin/env python3
"""
Octopus Energy Real Pricing API Integration
Fetches actual tariff rates, standing charges, and time-varying pricing data
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import os
from dataclasses import dataclass
import time


@dataclass
class TariffInfo:
    """Data class to store tariff information"""
    tariff_code: str
    product_code: str
    standing_charge: float  # pence per day
    unit_rate: Optional[float]  # pence per kWh (None for variable rates)
    is_variable: bool
    is_export: bool
    region: str
    valid_from: datetime
    valid_to: Optional[datetime]


class OctopusPricingAPI:
    """Class to fetch real pricing data from Octopus Energy API"""
    
    def __init__(self, api_key: Optional[str] = None, account_number: Optional[str] = None):
        """Initialize the pricing API client"""
        self.api_key = api_key or os.getenv('OCTOPUS_API_KEY')
        self.account_number = account_number or os.getenv('OCTOPUS_ACCOUNT_NUMBER')
        self.base_url = "https://api.octopus.energy/v1"
        self.session = requests.Session()
        
        # Set up authentication if API key is available
        if self.api_key and self.api_key != 'your_api_key_here':
            self.session.auth = (self.api_key, '')
            self.authenticated = True
        else:
            self.authenticated = False
    
    def get_historical_pricing_data(self, tariff_code: str, start_date: datetime, end_date: datetime, 
                                  is_export: bool = False) -> pd.DataFrame:
        """
        Fetch historical pricing data for a variable tariff (like Agile)
        
        Args:
            tariff_code: The tariff code (e.g., E-1R-AGILE-24-10-01-B)
            start_date: Start date for pricing data
            end_date: End date for pricing data
            is_export: Whether this is an export tariff
            
        Returns:
            DataFrame with columns: valid_from, valid_to, rate_inc_vat, rate_exc_vat
        """
        print(f"🔍 Fetching historical pricing data for {tariff_code}...")
        
        # Extract product code from tariff code
        parts = tariff_code.split('-')
        if len(parts) >= 4:
            product_code = '-'.join(parts[2:-1])
        else:
            print(f"❌ Invalid tariff code format: {tariff_code}")
            return pd.DataFrame()
        
        # Build URL for pricing data
        url = f"{self.base_url}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
        
        all_rates = []
        current_date = start_date
        
        # Fetch data in chunks to handle large date ranges
        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=30), end_date)
            
            params = {
                'period_from': current_date.strftime('%Y-%m-%dT00:00:00Z'),
                'period_to': chunk_end.strftime('%Y-%m-%dT23:59:59Z'),
                'page_size': 1500  # Maximum allowed
            }
            
            try:
                print(f"  📅 Fetching rates for {current_date.date()} to {chunk_end.date()}")
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                rates = data.get('results', [])
                all_rates.extend(rates)
                
                # Handle pagination
                next_url = data.get('next')
                while next_url:
                    response = self.session.get(next_url)
                    response.raise_for_status()
                    data = response.json()
                    rates = data.get('results', [])
                    all_rates.extend(rates)
                    next_url = data.get('next')
                
                # Rate limiting
                time.sleep(0.2)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching pricing data: {e}")
                break
            
            current_date = chunk_end
        
        if not all_rates:
            print(f"⚠️  No pricing data found for {tariff_code}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_rates)
        
        # Convert timestamps
        df['valid_from'] = pd.to_datetime(df['valid_from'], utc=True)
        df['valid_to'] = pd.to_datetime(df['valid_to'], utc=True)
        
        # Rename columns for clarity
        df = df.rename(columns={
            'value_inc_vat': 'rate_inc_vat',
            'value_exc_vat': 'rate_exc_vat'
        })
        
        # Sort by valid_from
        df = df.sort_values('valid_from').reset_index(drop=True)
        
        print(f"✅ Retrieved {len(df)} pricing periods for {tariff_code}")
        print(f"   📅 Date range: {df['valid_from'].min()} to {df['valid_to'].max()}")
        print(f"   💰 Rate range: {df['rate_inc_vat'].min():.2f}p - {df['rate_inc_vat'].max():.2f}p/kWh")
        
        return df[['valid_from', 'valid_to', 'rate_inc_vat', 'rate_exc_vat']]
    
    def match_consumption_with_pricing(self, consumption_df: pd.DataFrame, 
                                     import_pricing_df: pd.DataFrame,
                                     export_pricing_df: Optional[pd.DataFrame] = None,
                                     standing_charge_daily: float = 60.0) -> pd.DataFrame:
        """
        Match consumption data with actual pricing data by timestamp
        
        Args:
            consumption_df: DataFrame with consumption data (must have interval_start, consumption, meter_type)
            import_pricing_df: DataFrame with import pricing data
            export_pricing_df: DataFrame with export pricing data (optional)
            standing_charge_daily: Daily standing charge in pence
            
        Returns:
            DataFrame with consumption data plus actual pricing and costs
        """
        print("🔗 Matching consumption data with pricing...")
        
        if consumption_df.empty:
            return pd.DataFrame()
        
        # Make a copy to avoid modifying original
        result_df = consumption_df.copy()
        
        # Ensure interval_start is datetime with timezone
        if 'interval_start' not in result_df.columns:
            print("❌ Consumption data must have 'interval_start' column")
            return pd.DataFrame()
        
        result_df['interval_start'] = pd.to_datetime(result_df['interval_start'], utc=True)
        
        # Initialize pricing columns
        result_df['rate_inc_vat'] = None
        result_df['rate_exc_vat'] = None
        result_df['cost_exc_vat'] = None
        result_df['cost_inc_vat'] = None
        result_df['standing_charge'] = 0.0
        
        # Process import data
        import_mask = result_df['meter_type'] == 'import'
        if import_mask.any() and not import_pricing_df.empty:
            print(f"  📊 Processing {import_mask.sum()} import records...")
            result_df = self._match_pricing_for_meter_type(
                result_df, import_pricing_df, import_mask, standing_charge_daily
            )
        
        # Process export data
        export_mask = result_df['meter_type'] == 'export'
        if export_mask.any() and export_pricing_df is not None and not export_pricing_df.empty:
            print(f"  📊 Processing {export_mask.sum()} export records...")
            result_df = self._match_pricing_for_meter_type(
                result_df, export_pricing_df, export_mask, 0.0  # No standing charge for export
            )
        elif export_mask.any():
            print("  ⚠️  No export pricing data available, using fixed rate")
            # Use fixed export rate if no pricing data available
            fixed_export_rate = 15.0  # Default export rate
            result_df.loc[export_mask, 'rate_inc_vat'] = fixed_export_rate
            result_df.loc[export_mask, 'rate_exc_vat'] = fixed_export_rate / 1.05
            result_df.loc[export_mask, 'cost_inc_vat'] = result_df.loc[export_mask, 'consumption'] * fixed_export_rate
            result_df.loc[export_mask, 'cost_exc_vat'] = result_df.loc[export_mask, 'cost_inc_vat'] / 1.05
        
        # Calculate totals
        matched_records = result_df['rate_inc_vat'].notna().sum()
        total_records = len(result_df)
        match_percentage = (matched_records / total_records * 100) if total_records > 0 else 0
        
        print(f"✅ Pricing match complete:")
        print(f"   📊 {matched_records}/{total_records} records matched ({match_percentage:.1f}%)")
        
        if matched_records < total_records:
            unmatched = total_records - matched_records
            print(f"   ⚠️  {unmatched} records without pricing data (may be outside pricing data range)")
        
        return result_df
    
    def _match_pricing_for_meter_type(self, result_df: pd.DataFrame, pricing_df: pd.DataFrame, 
                                    mask: pd.Series, standing_charge_daily: float) -> pd.DataFrame:
        """Helper method to match pricing for a specific meter type"""
        
        for idx in result_df[mask].index:
            interval_start = result_df.at[idx, 'interval_start']
            consumption = result_df.at[idx, 'consumption']
            
            # Find matching pricing period
            matching_rates = pricing_df[
                (pricing_df['valid_from'] <= interval_start) & 
                (pricing_df['valid_to'] > interval_start)
            ]
            
            if not matching_rates.empty:
                # Use the first matching rate (should only be one)
                rate_inc_vat = matching_rates.iloc[0]['rate_inc_vat']
                rate_exc_vat = matching_rates.iloc[0]['rate_exc_vat']
                
                # Calculate costs
                cost_inc_vat = consumption * rate_inc_vat
                cost_exc_vat = consumption * rate_exc_vat
                
                # Add standing charge for import records (once per day)
                standing_charge = 0.0
                if standing_charge_daily > 0:
                    # Add standing charge proportionally (assuming 48 half-hours per day)
                    standing_charge = standing_charge_daily / 48.0
                
                # Update the result DataFrame
                result_df.at[idx, 'rate_inc_vat'] = rate_inc_vat
                result_df.at[idx, 'rate_exc_vat'] = rate_exc_vat
                result_df.at[idx, 'cost_inc_vat'] = cost_inc_vat
                result_df.at[idx, 'cost_exc_vat'] = cost_exc_vat
                result_df.at[idx, 'standing_charge'] = standing_charge
        
        return result_df
            
    def get_account_tariffs(self) -> List[TariffInfo]:
        """Get current tariff information from account data"""
        if not self.authenticated or not self.account_number:
            return []
            
        try:
            url = f"{self.base_url}/accounts/{self.account_number}/"
            response = self.session.get(url)
            response.raise_for_status()
            account_data = response.json()
            
            tariffs = []
            
            for property_info in account_data.get('properties', []):
                for meter_point in property_info.get('electricity_meter_points', []):
                    is_export = meter_point.get('is_export', False)
                    
                    # Get current agreements
                    agreements = meter_point.get('agreements', [])
                    if not agreements:
                        continue
                        
                    # Get the most recent active agreement
                    current_agreement = None
                    for agreement in agreements:
                        valid_from = datetime.fromisoformat(agreement['valid_from'].replace('Z', '+00:00'))
                        valid_to = agreement.get('valid_to')
                        valid_to = datetime.fromisoformat(valid_to.replace('Z', '+00:00')) if valid_to else None
                        
                        # Check if agreement is currently active
                        now = datetime.now(timezone.utc)
                        if valid_from <= now and (valid_to is None or valid_to > now):
                            current_agreement = agreement
                            break
                    
                    if current_agreement:
                        tariff_code = current_agreement['tariff_code']
                        tariff_info = self._get_tariff_details(tariff_code, is_export)
                        if tariff_info:
                            tariffs.append(tariff_info)
                            
            return tariffs
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching account tariffs: {e}")
            return []

    def _get_tariff_details(self, tariff_code: str, is_export: bool) -> Optional[TariffInfo]:
        """Get detailed tariff information from tariff code"""
        try:
            # Extract product code from tariff code
            parts = tariff_code.split('-')
            if len(parts) >= 4:
                product_code = '-'.join(parts[2:-1])
                region = parts[-1]
            else:
                return None
            
            # Get standing charges
            url = f"{self.base_url}/products/{product_code}/electricity-tariffs/{tariff_code}/standing-charges/"
            response = self.session.get(url)
            if response.status_code != 200:
                return None
                
            standing_charges = response.json()
            current_standing_charge = None
            
            # Get current standing charge
            now = datetime.now(timezone.utc)
            for charge in standing_charges.get('results', []):
                valid_from = datetime.fromisoformat(charge['valid_from'].replace('Z', '+00:00'))
                valid_to = charge.get('valid_to')
                valid_to = datetime.fromisoformat(valid_to.replace('Z', '+00:00')) if valid_to else None
                
                if valid_from <= now and (valid_to is None or valid_to > now):
                    current_standing_charge = charge['value_inc_vat']
                    break
            
            # Get unit rates
            url = f"{self.base_url}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
            response = self.session.get(url)
            
            unit_rate = None
            is_variable = False
            valid_from = None
            valid_to = None
            
            if response.status_code == 200:
                unit_rates = response.json()
                
                # Check if this is a variable tariff
                if len(unit_rates.get('results', [])) > 10:  # More than 10 rates suggests variable
                    is_variable = True
                else:
                    # Fixed rate - get current rate
                    for rate in unit_rates.get('results', []):
                        rate_valid_from = datetime.fromisoformat(rate['valid_from'].replace('Z', '+00:00'))
                        rate_valid_to = rate.get('valid_to')
                        rate_valid_to = datetime.fromisoformat(rate_valid_to.replace('Z', '+00:00')) if rate_valid_to else None
                        
                        if rate_valid_from <= now and (rate_valid_to is None or rate_valid_to > now):
                            unit_rate = rate['value_inc_vat']
                            valid_from = rate_valid_from
                            valid_to = rate_valid_to
                            break
            
            if current_standing_charge is None:
                return None
                
            return TariffInfo(
                tariff_code=tariff_code,
                product_code=product_code,
                standing_charge=current_standing_charge,
                unit_rate=unit_rate,
                is_variable=is_variable,
                is_export=is_export,
                region=region,
                valid_from=valid_from or now,
                valid_to=valid_to
            )
            
        except Exception as e:
            print(f"❌ Error getting tariff details for {tariff_code}: {e}")
            return None
    
    def create_pricing_config(self) -> Dict:
        """Create pricing configuration from real API data"""
        tariffs = self.get_account_tariffs()
        
        if not tariffs:
            # Return default config if no API data available
            from price_config import DEFAULT_TARIFFS
            print("📊 Using default UK energy tariffs")
            return DEFAULT_TARIFFS.copy()
        
        # Extract import and export rates
        import_tariff = None
        export_tariff = None
        
        for tariff in tariffs:
            if tariff.is_export:
                export_tariff = tariff
            else:
                import_tariff = tariff
        
        config = {}
        
        if import_tariff:
            config.update({
                'import_rate': import_tariff.unit_rate or 28.62,  # Fallback if variable
                'standing_charge_daily': import_tariff.standing_charge,
                'import_tariff_code': import_tariff.tariff_code,
                'import_is_variable': import_tariff.is_variable
            })
            print(f"✅ Using real import tariff: {import_tariff.tariff_code}")
            if import_tariff.is_variable:
                print(f"   Variable rate tariff (historical pricing can be fetched)")
            else:
                print(f"   Fixed rate: {import_tariff.unit_rate}p/kWh")
            print(f"   Standing charge: {import_tariff.standing_charge}p/day")
        
        if export_tariff:
            config.update({
                'export_rate': export_tariff.unit_rate or 15.0,  # Fallback if variable
                'export_tariff_code': export_tariff.tariff_code,
                'export_is_variable': export_tariff.is_variable
            })
            print(f"✅ Using real export tariff: {export_tariff.tariff_code}")
            if export_tariff.is_variable:
                print(f"   Variable rate tariff")
            else:
                print(f"   Fixed rate: {export_tariff.unit_rate}p/kWh")
        
        # Add standard fields
        config.update({
            'currency': 'GBP',
            'unit': 'pence',
            'data_source': 'octopus_api',
            'last_updated': datetime.now().isoformat()
        })
        
        # Fallback values if some tariffs not found
        if 'import_rate' not in config:
            config['import_rate'] = 28.62
            print("⚠️  Import rate not found, using default: 28.62p/kWh")
            
        if 'export_rate' not in config:
            config['export_rate'] = 15.0
            print("⚠️  Export rate not found, using default: 15.0p/kWh")
            
        if 'standing_charge_daily' not in config:
            config['standing_charge_daily'] = 60.10
            print("⚠️  Standing charge not found, using default: 60.10p/day")
        
        return config


def test_pricing_api():
    """Test function to demonstrate API usage"""
    print("🔍 Testing Octopus Energy Pricing API...")
    
    api = OctopusPricingAPI()
    
    if not api.authenticated:
        print("⚠️  No API credentials found. Set environment variables:")
        print("   export OCTOPUS_API_KEY='your_api_key'")
        print("   export OCTOPUS_ACCOUNT_NUMBER='A-AAAA1111'")
        print("\n📊 Testing with default pricing...")
    
    # Get pricing configuration
    config = api.create_pricing_config()
    
    print(f"\n💰 Pricing Configuration:")
    print(f"   Import rate: {config.get('import_rate')}p/kWh")
    print(f"   Export rate: {config.get('export_rate')}p/kWh")
    print(f"   Standing charge: {config.get('standing_charge_daily')}p/day")
    print(f"   Data source: {config.get('data_source', 'default')}")
    
    return config


if __name__ == "__main__":
    test_pricing_api()
