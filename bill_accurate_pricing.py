#!/usr/bin/env python3
"""
Bill-accurate pricing processor using real tariff data extracted from bills.
"""

import json
import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Optional
import pytz

class BillAccuratePricingProcessor:
    """Process pricing using bill-accurate tariff configuration."""
    
    def __init__(self, config_file: str = 'flexible_tariff_config.json'):
        self.config_file = config_file
        self.tariff_periods = []
        self.load_configuration()
    
    def load_configuration(self):
        """Load the tariff configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
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
    
    def get_time_of_use_rate(self, timestamp: datetime, period: Dict) -> float:
        """Get the appropriate rate for time-of-use tariff."""
        # Convert to UK timezone if needed
        if timestamp.tzinfo is None:
            uk_tz = pytz.timezone('Europe/London')
            timestamp = uk_tz.localize(timestamp)
        elif timestamp.tzinfo != pytz.timezone('Europe/London'):
            timestamp = timestamp.astimezone(pytz.timezone('Europe/London'))
        
        time_only = timestamp.time()
        
        # Find matching time-of-use rate
        for rate in period['time_of_use_rates']:
            start_time = datetime.strptime(rate['start_time'], '%H:%M').time()
            end_time = datetime.strptime(rate['end_time'], '%H:%M').time()
            
            # Handle time ranges that cross midnight
            if start_time <= end_time:
                # Normal range (e.g., 07:00-23:00)
                if start_time <= time_only < end_time:
                    return rate['rate_pence_per_kwh']
            else:
                # Range crosses midnight (e.g., 23:00-07:00)
                if time_only >= start_time or time_only < end_time:
                    return rate['rate_pence_per_kwh']
        
        # Fallback to first rate if no match
        return period['time_of_use_rates'][0]['rate_pence_per_kwh']
    
    def process_consumption_data(self, consumption_data: pd.DataFrame) -> pd.DataFrame:
        """Add accurate pricing to consumption data."""
        
        # Create a copy to avoid modifying original
        data = consumption_data.copy()
        
        # Add pricing columns
        data['rate_pence_per_kwh'] = 0.0
        data['cost_pence'] = 0.0
        data['tariff_period'] = ''
        data['rate_type'] = ''
        data['tariff_code'] = ''
        
        for timestamp, row in data.iterrows():
            consumption_kwh = row['consumption']
            
            # Find tariff period
            tariff_period = self.find_tariff_period(timestamp)
            
            if tariff_period is None:
                continue
            
            # Get rate
            if tariff_period['rate_type'] == 'time_of_use':
                rate = self.get_time_of_use_rate(timestamp, tariff_period)
                rate_type = f"Day/Night ({tariff_period['tariff_code']})"
            else:
                rate = tariff_period['rate_pence_per_kwh']
                rate_type = f"Fixed ({tariff_period['tariff_code']})"
            
            # Calculate cost
            cost_pence = consumption_kwh * rate
            
            # Update data
            data.loc[timestamp, 'rate_pence_per_kwh'] = rate
            data.loc[timestamp, 'cost_pence'] = cost_pence
            data.loc[timestamp, 'tariff_period'] = f"{tariff_period['start_date']} to {tariff_period['end_date']}"
            data.loc[timestamp, 'rate_type'] = rate_type
            data.loc[timestamp, 'tariff_code'] = tariff_period['tariff_code']
        
        return data
    
    def get_tariff_transitions(self, start_date: str, end_date: str) -> List[Dict]:
        """Get tariff transition dates within a date range."""
        transitions = []
        
        for period in self.tariff_periods:
            transition_date = period['start_date']
            
            # Check if transition is within our date range
            if start_date <= transition_date <= end_date:
                # Get rates for annotation
                if period['rate_type'] == 'time_of_use':
                    day_rate = next((rate['rate_pence_per_kwh'] for rate in period['time_of_use_rates'] 
                                   if rate['rate_name'] == 'Day'), 0)
                    night_rate = next((rate['rate_pence_per_kwh'] for rate in period['time_of_use_rates'] 
                                     if rate['rate_name'] == 'Night'), 0)
                    rate_text = f"Day: {day_rate}p, Night: {night_rate}p"
                else:
                    rate_text = f"{period['rate_pence_per_kwh']}p/kWh"
                
                transitions.append({
                    'date': transition_date,
                    'tariff_code': period['tariff_code'],
                    'rate_type': period['rate_type'],
                    'rate_text': rate_text,
                    'standing_charge': period['standing_charge_pence_per_day'],
                    'notes': period.get('notes', '')
                })
        
        return transitions
    
    def create_price_series(self, start_date: str, end_date: str, frequency: str = 'D') -> pd.DataFrame:
        """Create a price series for plotting (useful for Agile-style variable pricing)."""
        
        # Create date range
        if frequency == 'D':
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        elif frequency == 'H':
            date_range = pd.date_range(start=start_date, end=end_date, freq='H')
        else:
            date_range = pd.date_range(start=start_date, end=end_date, freq='30min')
        
        price_data = []
        
        for timestamp in date_range:
            tariff_period = self.find_tariff_period(timestamp)
            
            if tariff_period is None:
                continue
            
            # Get rate for this time
            if tariff_period['rate_type'] == 'time_of_use':
                rate = self.get_time_of_use_rate(timestamp, tariff_period)
                rate_type = 'time_of_use'
            else:
                rate = tariff_period['rate_pence_per_kwh']
                rate_type = 'fixed'
            
            price_data.append({
                'timestamp': timestamp,
                'rate_pence_per_kwh': rate,
                'tariff_code': tariff_period['tariff_code'],
                'rate_type': rate_type,
                'standing_charge': tariff_period['standing_charge_pence_per_day']
            })
        
        return pd.DataFrame(price_data)
    
    def is_agile_tariff(self, tariff_code: str) -> bool:
        """Check if a tariff code represents an Agile tariff."""
        return 'AGILE' in tariff_code.upper() if tariff_code else False

def main():
    """Test the bill-accurate pricing processor."""
    print("🧾 BILL-ACCURATE PRICING PROCESSOR TEST")
    print("=" * 50)
    
    processor = BillAccuratePricingProcessor()
    
    if not processor.tariff_periods:
        print("❌ No tariff periods loaded")
        return
    
    # Test with sample consumption data
    sample_data = pd.DataFrame({
        'consumption': [0.5, 0.8, 1.2, 0.3, 0.4, 0.6]
    }, index=pd.date_range('2023-04-05 08:00:00', periods=6, freq='4H'))
    
    print("\n📊 Sample consumption data:")
    print(sample_data)
    
    # Process the data
    processed_data = processor.process_consumption_data(sample_data)
    
    print("\n💰 Processed with bill-accurate pricing:")
    print(processed_data[['consumption', 'rate_pence_per_kwh', 'cost_pence', 'rate_type']])

if __name__ == "__main__":
    main() 