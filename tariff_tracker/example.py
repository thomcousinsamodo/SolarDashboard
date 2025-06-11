"""
Example script demonstrating how to use the Octopus Tariff Tracker.

This script shows how to:
1. Set up import and export tariff timelines
2. Fetch rates from the Octopus API
3. Look up rates for specific times
4. Validate timeline configuration
"""

from datetime import date, datetime
import time

from .timeline_manager import TimelineManager
from .models import TariffType, FlowDirection
from .logging_config import setup_logging, get_logger


def run_example():
    """Run the example demonstration."""
    # Set up detailed logging for the example
    setup_logging(log_level="INFO")
    logger = get_logger('example')
    
    logger.info("Starting Octopus Tariff Tracker Example")
    
    # Initialize the timeline manager
    manager = TimelineManager("example_config.json")
    
    print("🐙 Octopus Tariff Tracker Example")
    print("=" * 40)
    
    # Example 1: Add some tariff periods
    print("\n1. Adding example tariff periods...")
    
    try:
        # Check if we already have periods configured
        if not manager.config.import_timeline.periods:
            # Add an Agile import period (current)
            agile_period = manager.add_import_period(
                start_date=date(2024, 1, 1),
                end_date=None,  # Ongoing
                product_code="AGILE-FLEX-22-11-25",
                display_name="Agile Octopus Import",
                tariff_type=TariffType.AGILE,
                region="C",
                notes="Half-hourly pricing based on wholesale costs"
            )
            print(f"✓ Added: {agile_period.display_name}")
            
            # Add a fixed tariff period (historical, non-overlapping)
            fixed_period = manager.add_import_period(
                start_date=date(2022, 1, 1),
                end_date=date(2023, 12, 31),
                product_code="VAR-22-11-01",
                display_name="Flexible Octopus",
                tariff_type=TariffType.VARIABLE,
                region="C",
                notes="Previous standard variable tariff"
            )
            print(f"✓ Added: {fixed_period.display_name}")
        else:
            print("✓ Using existing import periods")
            agile_period = None
            for period in manager.config.import_timeline.periods:
                if period.tariff_type == TariffType.AGILE and period.end_date is None:
                    agile_period = period
                    break
        
        # Add export period if not exists
        if not manager.config.export_timeline.periods:
            # Use a valid export product code
            export_period = manager.add_export_period(
                start_date=date(2024, 1, 1),
                end_date=None,
                product_code="AGILE-OUTGOING-19-05-13",
                display_name="Agile Outgoing",
                tariff_type=TariffType.AGILE,
                region="C",
                notes="Agile export rates for solar generation"
            )
            print(f"✓ Added: {export_period.display_name}")
        else:
            print("✓ Using existing export periods")
            export_period = manager.config.export_timeline.periods[0] if manager.config.export_timeline.periods else None
        
    except Exception as e:
        print(f"❌ Error adding periods: {e}")
        logger.error(f"Failed to add example periods: {e}")
        return
    
    # Example 2: Fetch rates for periods
    print("\n2. Fetching rates from Octopus API...")
    
    try:
        # Fetch rates for the agile period if we have one
        if agile_period:
            print(f"Fetching recent rates for {agile_period.display_name}...")
            manager.fetch_rates_for_period(agile_period)
            print(f"✓ Fetched {len(agile_period.rates)} rates and {len(agile_period.standing_charges)} standing charges")
        
        # Small delay to be nice to the API
        time.sleep(1)
        
        # Fetch rates for export period if we have one
        if export_period:
            print(f"Fetching recent rates for {export_period.display_name}...")
            try:
                manager.fetch_rates_for_period(export_period)
                print(f"✓ Fetched {len(export_period.rates)} rates and {len(export_period.standing_charges)} standing charges")
            except Exception as e:
                print(f"⚠️  Could not fetch export rates (may be outdated product): {e}")
        else:
            print("⚠️  No export period configured")
        
    except Exception as e:
        print(f"❌ Error fetching rates: {e}")
        logger.error(f"Failed to fetch rates: {e}")
        # Continue with example even if API calls fail
    
    # Example 3: Save configuration
    print("\n3. Saving configuration...")
    try:
        manager.save_config()
        print("✓ Configuration saved to example_config.json")
    except Exception as e:
        print(f"❌ Error saving config: {e}")
    
    # Example 4: Show timeline summary
    print("\n4. Timeline Summary:")
    summary = manager.get_timeline_summary()
    print(f"Import periods: {summary['import_periods']}")
    print(f"Export periods: {summary['export_periods']}")
    print(f"Active import: {summary['import_active']}")
    print(f"Active export: {summary['export_active']}")
    
    # Example 5: Rate lookups
    print("\n5. Example rate lookups:")
    
    # Use a date from January 2025 when we have data  
    test_date = datetime(2025, 1, 1, 12, 0, 0)
    import_rate = manager.get_rate_at_datetime(test_date, FlowDirection.IMPORT)
    if import_rate:
        print(f"Import rate at {test_date}: {import_rate.value_inc_vat:.4f}p/kWh (valid from {import_rate.valid_from})")
    else:
        print(f"No import rate found for {test_date}")
    
    # Look up current export rate
    export_rate = manager.get_rate_at_datetime(test_date, FlowDirection.EXPORT)
    if export_rate:
        print(f"Export rate at {test_date}: {export_rate.value_inc_vat:.4f}p/kWh (valid from {export_rate.valid_from})")
    else:
        print(f"No export rate found for {test_date}")
    
    # Example 6: Timeline validation
    print("\n6. Timeline Validation:")
    validation = manager.validate_timelines()
    
    for timeline_name, issues in validation.items():
        print(f"{timeline_name.title()} timeline:")
        if any(issues.values()):
            if issues['gaps']:
                print(f"  ⚠️  {len(issues['gaps'])} gaps found")
            if issues['overlaps']:
                print(f"  ⚠️  {len(issues['overlaps'])} overlaps found")
            if issues['invalid_periods']:
                print(f"  ❌ {len(issues['invalid_periods'])} invalid periods")
        else:
            print("  ✓ No issues found")
    
    # Example 7: Show rate statistics if we have data
    if agile_period and agile_period.rates:
        print(f"\n7. Rate Statistics for {agile_period.display_name}:")
        rates = [r.value_inc_vat for r in agile_period.rates]
        print(f"Rates loaded: {len(rates)}")
        print(f"Min rate: {min(rates):.4f}p/kWh")
        print(f"Max rate: {max(rates):.4f}p/kWh")
        print(f"Average rate: {sum(rates)/len(rates):.4f}p/kWh")
        
        # Show some recent rates
        print("\nRecent rates (last 5):")
        for rate in sorted(agile_period.rates, key=lambda r: r.valid_from)[-5:]:
            print(f"  {rate.valid_from.strftime('%Y-%m-%d %H:%M')}: {rate.value_inc_vat:.4f}p/kWh")
    
    print("\n" + "=" * 40)
    print("Example completed! Check the logs/ directory for detailed logs.")
    print("Configuration saved to example_config.json")
    
    logger.info("Example completed successfully")


if __name__ == '__main__':
    run_example() 