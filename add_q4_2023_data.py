#!/usr/bin/env python3
"""
Add Q4 2023 real bill data to enhanced tariff configuration
"""

from enhanced_tariff_configuration import EnhancedTariffConfigurationManager, EnhancedTariffPeriod, TimeOfUseRate

def add_q4_2023_real_data():
    """Add real Q4 2023 bill data"""
    
    print("📄 Adding Q4 2023 REAL bill data...")
    
    # Load existing configuration
    manager = EnhancedTariffConfigurationManager('enhanced_tariff_config.json')
    
    # Create Q4 2023 period with REAL bill data
    q4_2023_period = EnhancedTariffPeriod(
        name="Flexible Octopus Q4 2023",
        tariff_code="E-1R-FLEX-22-11-25-B",
        start_date="2023-12-01",
        end_date="2024-02-29",
        is_variable=False,
        is_export=False,
        standing_charge=46.43,  # Real data from bill
        time_of_use_rates=[
            TimeOfUseRate("Night", 15.01, "23:00", "07:00", "Cheap night rate - REAL BILL DATA"),
            TimeOfUseRate("Day", 25.01, "07:00", "23:00", "Standard day rate - REAL BILL DATA")
        ],
        description="REAL BILL DATA from Q4 2023 - Day: 25.01p, Night: 15.01p, Standing: 46.43p"
    )
    
    # Find the right position to insert (after Q3 2023, before Q2 2024)
    insert_position = len(manager.tariff_periods)
    for i, period in enumerate(manager.tariff_periods):
        if not period.is_export and period.start_date > "2023-12-01":
            insert_position = i
            break
    
    # Check if Q4 2023 already exists
    existing_q4 = None
    for i, period in enumerate(manager.tariff_periods):
        if ("Q4 2023" in period.name or 
            (period.start_date == "2023-12-01" and not period.is_export)):
            existing_q4 = i
            break
    
    if existing_q4 is not None:
        print(f"🔄 Updating existing Q4 2023 period...")
        manager.tariff_periods[existing_q4] = q4_2023_period
    else:
        print(f"➕ Adding new Q4 2023 period at position {insert_position}...")
        manager.tariff_periods.insert(insert_position, q4_2023_period)
    
    # Save updated configuration
    manager.save_configuration()
    
    print("✅ Q4 2023 REAL bill data added successfully!")
    print("\n📋 Updated Configuration:")
    manager.print_configuration()
    
    print("\n💡 What we now have:")
    print("   ✅ Q2 2023: Estimated rates")
    print("   ✅ Q3 2023: Estimated rates") 
    print("   ✅ Q4 2023: REAL BILL DATA ← NEW!")
    print("   ✅ Q2 2024: Estimated rates")
    print("   ✅ Agile: Variable rates from API")
    
    print("\n🎯 Next steps:")
    print("   1. Add Q1 2024 data if you have that bill")
    print("   2. Update Q2/Q3 2023 with real bill data when found")
    print("   3. Process full dataset with ultimate pricing")

if __name__ == "__main__":
    add_q4_2023_real_data() 