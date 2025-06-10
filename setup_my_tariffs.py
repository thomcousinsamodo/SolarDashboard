#!/usr/bin/env python3
"""
Quick setup script for your specific tariff configuration
"""

from tariff_configuration import TariffConfigurationManager, TariffPeriod

def setup_your_tariffs():
    """Set up your specific tariff configuration"""
    
    print("🔧 Setting up your tariff configuration...")
    
    # Create manager
    manager = TariffConfigurationManager('tariff_config.json')
    
    # Your specific tariff history
    manager.tariff_periods = [
        TariffPeriod(
            name="Flexible Octopus (Pre-Agile)",
            tariff_code="E-1R-FLEX-22-11-25-B",  # Common Flexible tariff code
            start_date="2023-06-01",
            end_date="2024-06-05",
            is_variable=False,
            is_export=False,
            fixed_rate=28.62,  # Typical flexible rate around that time
            standing_charge=54.85,
            description="Fixed rate tariff before switching to Agile on 6th June 2024"
        ),
        TariffPeriod(
            name="Agile Octopus (From June 2024)",
            tariff_code="E-1R-AGILE-24-10-01-B",  # Your current tariff from API
            start_date="2024-06-06",
            end_date=None,  # Ongoing
            is_variable=True,
            is_export=False,
            standing_charge=54.85,
            description="Variable rate tariff with 30-minute pricing from 6th June 2024"
        ),
        TariffPeriod(
            name="Export Tariff (Ongoing)",
            tariff_code="E-1R-OUTGOING-VAR-24-10-26-B",  # Your current export tariff
            start_date="2023-06-01",
            end_date=None,  # Ongoing
            is_variable=False,
            is_export=True,
            fixed_rate=15.0,
            description="Fixed export rate throughout all periods"
        )
    ]
    
    # Save configuration
    manager.save_configuration()
    
    print("✅ Configuration created successfully!")
    print("\n📋 Your Tariff Configuration:")
    manager.print_configuration()
    
    print("\n💡 Notes:")
    print("   • If you find your exact pre-Agile tariff code later, you can edit tariff_config.json")
    print("   • The tariff code doesn't affect fixed-rate calculations")
    print("   • What matters most is the rate (28.62p/kWh) and dates")
    print("   • For Agile periods, we fetch real API data regardless of tariff code")

if __name__ == "__main__":
    setup_your_tariffs() 