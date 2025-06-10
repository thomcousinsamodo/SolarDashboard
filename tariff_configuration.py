#!/usr/bin/env python3
"""
Tariff Configuration System
Handles multiple tariff periods with different pricing structures over time
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import os


@dataclass
class TariffPeriod:
    """Configuration for a specific tariff period"""
    name: str
    tariff_code: str
    start_date: str  # ISO format: YYYY-MM-DD
    end_date: Optional[str]  # ISO format: YYYY-MM-DD, None for ongoing
    is_variable: bool
    is_export: bool
    fixed_rate: Optional[float] = None  # pence/kWh, used if not variable
    standing_charge: Optional[float] = None  # pence/day
    description: str = ""

    def get_start_datetime(self) -> datetime:
        """Convert start_date string to datetime"""
        return datetime.fromisoformat(self.start_date + 'T00:00:00+00:00')
    
    def get_end_datetime(self) -> Optional[datetime]:
        """Convert end_date string to datetime"""
        if self.end_date:
            return datetime.fromisoformat(self.end_date + 'T23:59:59+00:00')
        return None


class TariffConfigurationManager:
    """Manages tariff configurations and periods"""
    
    def __init__(self, config_file: str = 'tariff_config.json'):
        self.config_file = config_file
        self.tariff_periods: List[TariffPeriod] = []
        self.load_configuration()
    
    def load_configuration(self):
        """Load tariff configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                self.tariff_periods = []
                for period_data in data.get('tariff_periods', []):
                    period = TariffPeriod(**period_data)
                    self.tariff_periods.append(period)
                
                print(f"✅ Loaded {len(self.tariff_periods)} tariff periods from {self.config_file}")
                
            except Exception as e:
                print(f"⚠️  Error loading configuration: {e}")
                self._create_default_configuration()
        else:
            print(f"📁 Configuration file not found, creating default: {self.config_file}")
            self._create_default_configuration()
    
    def _create_default_configuration(self):
        """Create a default configuration based on the user's scenario"""
        # Based on the user's description
        self.tariff_periods = [
            TariffPeriod(
                name="Flexible Octopus (Pre-Agile)",
                tariff_code="E-1R-VAR-22-11-01-B",  # Example flexible tariff
                start_date="2023-06-01",
                end_date="2024-06-05",
                is_variable=False,
                is_export=False,
                fixed_rate=28.62,  # Default flexible rate
                standing_charge=54.85,
                description="Fixed rate tariff before switching to Agile"
            ),
            TariffPeriod(
                name="Agile Octopus (Current)",
                tariff_code="E-1R-AGILE-24-10-01-B",
                start_date="2024-06-06",
                end_date=None,  # Ongoing
                is_variable=True,
                is_export=False,
                standing_charge=54.85,
                description="Variable rate tariff with 30-minute pricing"
            ),
            TariffPeriod(
                name="Export Tariff",
                tariff_code="E-1R-OUTGOING-VAR-24-10-26-B",
                start_date="2023-06-01",
                end_date=None,  # Ongoing
                is_variable=False,
                is_export=True,
                fixed_rate=15.0,
                description="Fixed export rate throughout"
            )
        ]
        self.save_configuration()
    
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            data = {
                'tariff_periods': [asdict(period) for period in self.tariff_periods],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Configuration saved to {self.config_file}")
            
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
    
    def add_tariff_period(self, period: TariffPeriod):
        """Add a new tariff period"""
        self.tariff_periods.append(period)
        self.save_configuration()
        print(f"✅ Added tariff period: {period.name}")
    
    def get_tariff_for_date(self, target_date: datetime, is_export: bool = False) -> Optional[TariffPeriod]:
        """Get the applicable tariff for a specific date"""
        for period in self.tariff_periods:
            if period.is_export != is_export:
                continue
                
            start_dt = period.get_start_datetime()
            end_dt = period.get_end_datetime()
            
            if start_dt <= target_date and (end_dt is None or target_date <= end_dt):
                return period
        
        return None
    
    def get_tariff_periods_for_range(self, start_date: datetime, end_date: datetime, 
                                   is_export: bool = False) -> List[Tuple[TariffPeriod, datetime, datetime]]:
        """
        Get all tariff periods that overlap with the given date range
        Returns list of (tariff_period, period_start, period_end) tuples
        """
        overlapping_periods = []
        
        for period in self.tariff_periods:
            if period.is_export != is_export:
                continue
            
            period_start = period.get_start_datetime()
            period_end = period.get_end_datetime() or datetime.now().replace(tzinfo=period_start.tzinfo)
            
            # Check if periods overlap
            if period_start <= end_date and period_end >= start_date:
                # Calculate the actual overlap
                overlap_start = max(period_start, start_date)
                overlap_end = min(period_end, end_date)
                
                overlapping_periods.append((period, overlap_start, overlap_end))
        
        # Sort by start date
        overlapping_periods.sort(key=lambda x: x[1])
        
        return overlapping_periods
    
    def print_configuration(self):
        """Print current tariff configuration"""
        print("\n📋 Current Tariff Configuration:")
        print("=" * 60)
        
        for i, period in enumerate(self.tariff_periods):
            meter_type = "Export" if period.is_export else "Import"
            end_date = period.end_date or "Ongoing"
            rate_info = ""
            
            if period.is_variable:
                rate_info = "Variable rates (fetched from API)"
            else:
                rate_info = f"Fixed: {period.fixed_rate}p/kWh"
            
            print(f"\n{i+1}. {period.name} ({meter_type})")
            print(f"   📅 Period: {period.start_date} to {end_date}")
            print(f"   🏷️  Tariff: {period.tariff_code}")
            print(f"   💰 Rates: {rate_info}")
            if period.standing_charge:
                print(f"   📊 Standing: {period.standing_charge}p/day")
            if period.description:
                print(f"   📝 Notes: {period.description}")
    
    def interactive_setup(self):
        """Interactive setup for new users"""
        print("\n🔧 Interactive Tariff Configuration Setup")
        print("=" * 50)
        print("This will help you configure your tariff history for accurate pricing.")
        print("\nTip: You can find tariff codes in your Octopus Energy bills or account dashboard.")
        
        self.tariff_periods = []
        
        # Get current tariffs from API if possible
        try:
            from octopus_pricing_api import OctopusPricingAPI
            api = OctopusPricingAPI()
            if api.authenticated:
                current_tariffs = api.get_account_tariffs()
                if current_tariffs:
                    print(f"\n📡 Found current tariffs from your account:")
                    for tariff in current_tariffs:
                        meter_type = "Export" if tariff.is_export else "Import"
                        variable_text = "Variable" if tariff.is_variable else "Fixed"
                        print(f"   • {tariff.tariff_code} ({meter_type}, {variable_text})")
        except:
            pass
        
        # Add tariff periods interactively
        while True:
            print(f"\n--- Adding Tariff Period {len(self.tariff_periods) + 1} ---")
            
            name = input("Tariff name (e.g., 'Flexible Octopus', 'Agile Summer 2024'): ").strip()
            if not name:
                break
            
            tariff_code = input("Tariff code (e.g., E-1R-AGILE-24-10-01-B): ").strip()
            start_date = input("Start date (YYYY-MM-DD): ").strip()
            end_date = input("End date (YYYY-MM-DD, or press Enter if ongoing): ").strip() or None
            
            is_export = input("Is this an export tariff? (y/n): ").lower().startswith('y')
            is_variable = input("Is this a variable rate tariff (like Agile)? (y/n): ").lower().startswith('y')
            
            fixed_rate = None
            if not is_variable:
                rate_input = input("Fixed rate (pence/kWh): ").strip()
                if rate_input:
                    fixed_rate = float(rate_input)
            
            standing_charge = None
            if not is_export:
                sc_input = input("Standing charge (pence/day, or press Enter to skip): ").strip()
                if sc_input:
                    standing_charge = float(sc_input)
            
            description = input("Description (optional): ").strip()
            
            period = TariffPeriod(
                name=name,
                tariff_code=tariff_code,
                start_date=start_date,
                end_date=end_date,
                is_variable=is_variable,
                is_export=is_export,
                fixed_rate=fixed_rate,
                standing_charge=standing_charge,
                description=description
            )
            
            self.tariff_periods.append(period)
            print(f"✅ Added: {period.name}")
            
            if input("\nAdd another tariff period? (y/n): ").lower().startswith('n'):
                break
        
        if self.tariff_periods:
            self.save_configuration()
            print(f"\n🎉 Configuration complete! Added {len(self.tariff_periods)} tariff periods.")
            self.print_configuration()
        else:
            print("\n📁 No tariff periods added. Using default configuration.")
            self._create_default_configuration()


def create_sample_configuration():
    """Create a sample configuration file for the user's scenario"""
    manager = TariffConfigurationManager('sample_tariff_config.json')
    
    # Add the user's specific scenario
    periods = [
        TariffPeriod(
            name="Flexible Octopus (Pre-Agile)",
            tariff_code="E-1R-VAR-22-11-01-B",
            start_date="2023-06-01",
            end_date="2024-06-05",
            is_variable=False,
            is_export=False,
            fixed_rate=28.62,
            standing_charge=54.85,
            description="Fixed rate tariff before switching to Agile on 6th June 2024"
        ),
        TariffPeriod(
            name="Agile Octopus (Summer 2024)",
            tariff_code="E-1R-AGILE-24-10-01-B",
            start_date="2024-06-06",
            end_date="2024-10-31",  # Example end date
            is_variable=True,
            is_export=False,
            standing_charge=54.85,
            description="Variable rate tariff with 30-minute pricing"
        ),
        TariffPeriod(
            name="Cosy Octopus (Winter 2024)",
            tariff_code="E-1R-COSY-24-12-12-B",  # Example cosy tariff
            start_date="2024-11-01",
            end_date="2025-03-31",
            is_variable=False,
            is_export=False,
            fixed_rate=25.0,  # Example cosy rate
            standing_charge=54.85,
            description="Fixed winter tariff with cheaper heating rates"
        ),
        TariffPeriod(
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
    
    manager.tariff_periods = periods
    manager.save_configuration()
    
    print("📋 Sample tariff configuration created:")
    manager.print_configuration()


def main():
    """Command line interface for tariff configuration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage tariff configurations')
    parser.add_argument('--interactive', action='store_true', help='Interactive setup')
    parser.add_argument('--sample', action='store_true', help='Create sample configuration')
    parser.add_argument('--show', action='store_true', help='Show current configuration')
    parser.add_argument('--config-file', default='tariff_config.json', help='Configuration file path')
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_configuration()
    elif args.interactive:
        manager = TariffConfigurationManager(args.config_file)
        manager.interactive_setup()
    elif args.show:
        manager = TariffConfigurationManager(args.config_file)
        manager.print_configuration()
    else:
        print("Use --interactive, --sample, or --show")
        print("Example: python tariff_configuration.py --sample")


if __name__ == "__main__":
    main() 