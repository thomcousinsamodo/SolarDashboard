#!/usr/bin/env python3
"""
Enhanced Tariff Configuration System
Handles time-of-use pricing, day/night rates, and quarterly price changes
"""

import json
import pandas as pd
from datetime import datetime, timedelta, time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import os


@dataclass
class TimeOfUseRate:
    """Time-of-use rate definition"""
    name: str  # e.g., "Day", "Night", "Peak", "Off-Peak"
    rate_inc_vat: float  # pence/kWh
    start_time: str  # "HH:MM" format
    end_time: str  # "HH:MM" format
    description: str = ""

    def applies_to_time(self, check_time: time) -> bool:
        """Check if this rate applies to a given time"""
        start = time.fromisoformat(self.start_time)
        end = time.fromisoformat(self.end_time)
        
        # Handle overnight periods (e.g., 23:00 to 07:00)
        if start > end:
            return check_time >= start or check_time < end
        else:
            return start <= check_time < end


@dataclass
class EnhancedTariffPeriod:
    """Enhanced tariff period with time-of-use pricing support"""
    name: str
    tariff_code: str
    start_date: str  # ISO format: YYYY-MM-DD
    end_date: Optional[str]  # ISO format: YYYY-MM-DD, None for ongoing
    is_variable: bool  # True for API-fetched rates (like Agile)
    is_export: bool
    standing_charge: Optional[float] = None  # pence/day
    
    # Time-of-use rates (empty list means single rate in fixed_rate)
    time_of_use_rates: List[TimeOfUseRate] = None
    fixed_rate: Optional[float] = None  # Used if no time-of-use rates
    
    description: str = ""

    def __post_init__(self):
        if self.time_of_use_rates is None:
            self.time_of_use_rates = []

    def get_rate_for_time(self, check_time: datetime) -> Tuple[float, str]:
        """
        Get the applicable rate for a specific datetime
        Returns (rate_inc_vat, rate_name)
        """
        if not self.time_of_use_rates:
            # Simple fixed rate
            return self.fixed_rate or 0.0, "Fixed"
        
        time_only = check_time.time()
        
        for rate in self.time_of_use_rates:
            if rate.applies_to_time(time_only):
                return rate.rate_inc_vat, rate.name
        
        # Fallback to first rate if no match
        if self.time_of_use_rates:
            return self.time_of_use_rates[0].rate_inc_vat, self.time_of_use_rates[0].name
        
        return self.fixed_rate or 0.0, "Fixed"

    def get_start_datetime(self) -> datetime:
        """Convert start_date string to datetime"""
        return datetime.fromisoformat(self.start_date + 'T00:00:00+00:00')
    
    def get_end_datetime(self) -> Optional[datetime]:
        """Convert end_date string to datetime"""
        if self.end_date:
            return datetime.fromisoformat(self.end_date + 'T23:59:59+00:00')
        return None


class EnhancedTariffConfigurationManager:
    """Enhanced manager for complex tariff configurations"""
    
    def __init__(self, config_file: str = 'enhanced_tariff_config.json'):
        self.config_file = config_file
        self.tariff_periods: List[EnhancedTariffPeriod] = []
        self.load_configuration()
    
    def load_configuration(self):
        """Load enhanced tariff configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                self.tariff_periods = []
                for period_data in data.get('tariff_periods', []):
                    # Convert time_of_use_rates from dict to TimeOfUseRate objects
                    tou_rates = []
                    if 'time_of_use_rates' in period_data and period_data['time_of_use_rates']:
                        for rate_data in period_data['time_of_use_rates']:
                            tou_rates.append(TimeOfUseRate(**rate_data))
                    
                    period_data['time_of_use_rates'] = tou_rates
                    period = EnhancedTariffPeriod(**period_data)
                    self.tariff_periods.append(period)
                
                print(f"✅ Loaded {len(self.tariff_periods)} enhanced tariff periods from {self.config_file}")
                
            except Exception as e:
                print(f"⚠️  Error loading configuration: {e}")
                self._create_realistic_configuration()
        else:
            print(f"📁 Configuration file not found, creating realistic: {self.config_file}")
            self._create_realistic_configuration()
    
    def _create_realistic_configuration(self):
        """Create a realistic configuration based on the user's bill information"""
        
        # Create realistic Flexible Octopus periods with quarterly changes
        # Note: These are estimates - user should update with actual bill data
        
        self.tariff_periods = [
            # Flexible Octopus - Q2 2023 (estimated)
            EnhancedTariffPeriod(
                name="Flexible Octopus Q2 2023",
                tariff_code="E-1R-FLEX-22-11-25-B",
                start_date="2023-06-01",
                end_date="2023-08-31",
                is_variable=False,
                is_export=False,
                standing_charge=50.0,  # Estimated
                time_of_use_rates=[
                    TimeOfUseRate("Night", 11.50, "23:00", "07:00", "Cheap night rate"),
                    TimeOfUseRate("Day", 26.50, "07:00", "23:00", "Standard day rate")
                ],
                description="Estimated Q2 2023 Flexible rates - UPDATE WITH ACTUAL BILLS"
            ),
            
            # Flexible Octopus - Q3 2023 (estimated)
            EnhancedTariffPeriod(
                name="Flexible Octopus Q3 2023",
                tariff_code="E-1R-FLEX-22-11-25-B",
                start_date="2023-09-01",
                end_date="2023-11-30",
                is_variable=False,
                is_export=False,
                standing_charge=50.0,  # Estimated
                time_of_use_rates=[
                    TimeOfUseRate("Night", 12.00, "23:00", "07:00", "Cheap night rate"),
                    TimeOfUseRate("Day", 27.00, "07:00", "23:00", "Standard day rate")
                ],
                description="Estimated Q3 2023 Flexible rates - UPDATE WITH ACTUAL BILLS"
            ),
            
            # Continue with more quarters... (truncated for brevity)
            # User should add their actual quarterly rates
            
            # Flexible Octopus - Pre-Agile Final Quarter (estimated)
            EnhancedTariffPeriod(
                name="Flexible Octopus Q2 2024",
                tariff_code="E-1R-FLEX-22-11-25-B",
                start_date="2024-03-01",
                end_date="2024-06-05",
                is_variable=False,
                is_export=False,
                standing_charge=51.97,  # From the bill
                time_of_use_rates=[
                    TimeOfUseRate("Night", 12.80, "23:00", "07:00", "Cheap night rate"),
                    TimeOfUseRate("Day", 28.72, "07:00", "23:00", "Standard day rate")
                ],
                description="Estimated rates before Agile switch - UPDATE WITH ACTUAL BILLS"
            ),
            
            # Agile period (variable rates from API)
            EnhancedTariffPeriod(
                name="Agile Octopus (From June 2024)",
                tariff_code="E-1R-AGILE-24-10-01-B",
                start_date="2024-06-06",
                end_date=None,
                is_variable=True,
                is_export=False,
                standing_charge=54.85,
                description="Variable rate tariff with 30-minute pricing from 6th June 2024"
            ),
            
            # Export tariff (consistent throughout)
            EnhancedTariffPeriod(
                name="Export Tariff (Ongoing)",
                tariff_code="E-1R-OUTGOING-VAR-24-10-26-B",
                start_date="2023-06-01",
                end_date=None,
                is_variable=False,
                is_export=True,
                fixed_rate=15.0,
                description="Fixed export rate throughout all periods"
            )
        ]
        
        self.save_configuration()
    
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            # Convert TimeOfUseRate objects to dicts for JSON serialization
            periods_data = []
            for period in self.tariff_periods:
                period_dict = asdict(period)
                # Convert TimeOfUseRate objects to dicts
                if period_dict['time_of_use_rates']:
                    period_dict['time_of_use_rates'] = [
                        asdict(rate) for rate in period.time_of_use_rates
                    ]
                periods_data.append(period_dict)
            
            data = {
                'tariff_periods': periods_data,
                'last_updated': datetime.now().isoformat(),
                'format_version': '2.0_enhanced'
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Enhanced configuration saved to {self.config_file}")
            
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
    
    def print_configuration(self):
        """Print current enhanced tariff configuration"""
        print("\n📋 Enhanced Tariff Configuration:")
        print("=" * 80)
        
        for i, period in enumerate(self.tariff_periods):
            meter_type = "Export" if period.is_export else "Import"
            end_date = period.end_date or "Ongoing"
            
            print(f"\n{i+1}. {period.name} ({meter_type})")
            print(f"   📅 Period: {period.start_date} to {end_date}")
            print(f"   🏷️  Tariff: {period.tariff_code}")
            
            if period.is_variable:
                print(f"   💰 Rates: Variable (fetched from API)")
            elif period.time_of_use_rates:
                print(f"   💰 Rates: Time-of-Use")
                for rate in period.time_of_use_rates:
                    print(f"      🕐 {rate.name}: {rate.rate_inc_vat}p/kWh ({rate.start_time}-{rate.end_time})")
            else:
                print(f"   💰 Rates: Fixed {period.fixed_rate}p/kWh")
            
            if period.standing_charge:
                print(f"   📊 Standing: {period.standing_charge}p/day")
            if period.description:
                print(f"   📝 Notes: {period.description}")
    
    def get_tariff_for_date(self, target_date: datetime, is_export: bool = False) -> Optional[EnhancedTariffPeriod]:
        """Get the applicable tariff for a specific date"""
        for period in self.tariff_periods:
            if period.is_export != is_export:
                continue
                
            start_dt = period.get_start_datetime()
            end_dt = period.get_end_datetime()
            
            if start_dt <= target_date and (end_dt is None or target_date <= end_dt):
                return period
        
        return None

    def create_bill_input_helper(self):
        """Interactive helper to input quarterly bill data"""
        print("\n🧾 Bill Data Input Helper")
        print("=" * 50)
        print("This will help you input your actual quarterly Flexible Octopus rates from bills.")
        print("\nTip: Look for 'Unit Rate (Day)' and 'Unit Rate (Night)' on your bills")
        
        # Get existing periods to update
        flexible_periods = [p for p in self.tariff_periods if not p.is_export and not p.is_variable]
        
        print(f"\nFound {len(flexible_periods)} Flexible periods to update:")
        for i, period in enumerate(flexible_periods):
            print(f"{i+1}. {period.name} ({period.start_date} to {period.end_date})")
        
        while True:
            try:
                choice = input(f"\nEnter period number to update (1-{len(flexible_periods)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    break
                
                period_idx = int(choice) - 1
                if 0 <= period_idx < len(flexible_periods):
                    self._update_period_from_bill(flexible_periods[period_idx])
                else:
                    print("Invalid period number")
                    
            except ValueError:
                print("Please enter a valid number or 'q'")
        
        self.save_configuration()
        print("\n✅ Bill data updated!")
    
    def _update_period_from_bill(self, period: EnhancedTariffPeriod):
        """Update a period with actual bill data"""
        print(f"\n📄 Updating: {period.name}")
        print(f"📅 Period: {period.start_date} to {period.end_date}")
        
        day_rate = input(f"Day rate (current: {period.time_of_use_rates[1].rate_inc_vat if len(period.time_of_use_rates) > 1 else 'N/A'}p/kWh): ")
        night_rate = input(f"Night rate (current: {period.time_of_use_rates[0].rate_inc_vat if period.time_of_use_rates else 'N/A'}p/kWh): ")
        standing_charge = input(f"Standing charge (current: {period.standing_charge}p/day): ")
        
        # Update rates
        if day_rate:
            if len(period.time_of_use_rates) > 1:
                period.time_of_use_rates[1].rate_inc_vat = float(day_rate)
            else:
                period.time_of_use_rates.append(TimeOfUseRate("Day", float(day_rate), "07:00", "23:00", "Standard day rate"))
        
        if night_rate:
            if period.time_of_use_rates:
                period.time_of_use_rates[0].rate_inc_vat = float(night_rate)
            else:
                period.time_of_use_rates.append(TimeOfUseRate("Night", float(night_rate), "23:00", "07:00", "Cheap night rate"))
        
        if standing_charge:
            period.standing_charge = float(standing_charge)
        
        print(f"✅ Updated {period.name}")


def main():
    """Enhanced command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced tariff configuration with time-of-use support')
    parser.add_argument('--show', action='store_true', help='Show current configuration')
    parser.add_argument('--bills', action='store_true', help='Input quarterly bill data')
    parser.add_argument('--config-file', default='enhanced_tariff_config.json', help='Configuration file path')
    
    args = parser.parse_args()
    
    manager = EnhancedTariffConfigurationManager(args.config_file)
    
    if args.bills:
        manager.create_bill_input_helper()
    elif args.show:
        manager.print_configuration()
    else:
        print("✨ Enhanced Tariff Configuration System")
        print("Use --show to view configuration")
        print("Use --bills to input quarterly bill data")
        manager.print_configuration()


if __name__ == "__main__":
    main() 