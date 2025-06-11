"""
Command-line interface for the Octopus Tariff Tracker.
"""

from datetime import datetime, date
import argparse
import sys

from .timeline_manager import TimelineManager
from .models import TariffType, FlowDirection
from .logging_config import get_logger, setup_logging


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description='Octopus Tariff Tracker')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='Set logging level')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add period command
    add_parser = subparsers.add_parser('add', help='Add a new tariff period')
    add_parser.add_argument('--flow', choices=['import', 'export'], required=True,
                           help='Flow direction')
    add_parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    add_parser.add_argument('--end', help='End date (YYYY-MM-DD), optional')
    add_parser.add_argument('--product', required=True, help='Product code')
    add_parser.add_argument('--name', required=True, help='Display name')
    add_parser.add_argument('--type', choices=['fixed', 'variable', 'agile', 'economy7', 'go'], 
                           required=True, help='Tariff type')
    add_parser.add_argument('--region', default='C', help='Region code (default: C)')
    add_parser.add_argument('--notes', default='', help='Optional notes')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all tariff periods')
    
    # Refresh command
    refresh_parser = subparsers.add_parser('refresh', help='Refresh rates for all periods')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show timeline status')
    
    # Rate lookup command
    rate_parser = subparsers.add_parser('rate', help='Look up rate for specific datetime')
    rate_parser.add_argument('--datetime', required=True, 
                            help='DateTime in ISO format (YYYY-MM-DDTHH:MM:SS)')
    rate_parser.add_argument('--flow', choices=['import', 'export'], default='import',
                           help='Flow direction')
    # Note: Rate type is now automatically determined based on time and tariff type
    
    args = parser.parse_args()
    
    # Set up logging with specified level
    setup_logging(args.log_level)
    logger = get_logger('cli')
    
    if not args.command:
        parser.print_help()
        return
    
    logger.info(f"Starting Octopus Tariff Tracker CLI - Command: {args.command}")
    
    # Initialize timeline manager
    manager = TimelineManager()
    
    if args.command == 'add':
        add_period(manager, args)
    elif args.command == 'list':
        list_periods(manager)
    elif args.command == 'refresh':
        refresh_rates(manager)
    elif args.command == 'status':
        show_status(manager)
    elif args.command == 'rate':
        lookup_rate(manager, args)


def add_period(manager, args):
    """Add a new tariff period."""
    try:
        flow_direction = FlowDirection(args.flow)
        start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end, '%Y-%m-%d').date() if args.end else None
        tariff_type = TariffType(args.type)
        
        if flow_direction == FlowDirection.IMPORT:
            period = manager.add_import_period(
                start_date, end_date, args.product, args.name, 
                tariff_type, args.region, args.notes
            )
        else:
            period = manager.add_export_period(
                start_date, end_date, args.product, args.name, 
                tariff_type, args.region, args.notes
            )
        
        print(f"Added {args.flow} period: {args.name}")
        print(f"Fetching rates for period...")
        
        manager.fetch_rates_for_period(period)
        manager.save_config()
        
        print(f"Successfully added period with {len(period.rates)} rates")
        
    except Exception as e:
        print(f"Error adding period: {e}")
        sys.exit(1)


def list_periods(manager):
    """List all configured periods."""
    print("Import Timeline:")
    print("=" * 50)
    
    for i, period in enumerate(manager.config.import_timeline.periods):
        status = "ACTIVE" if period.is_active else "INACTIVE"
        end_str = period.end_date.strftime('%Y-%m-%d') if period.end_date else "Ongoing"
        
        print(f"{i+1}. {period.display_name}")
        print(f"   {period.start_date} - {end_str} [{status}]")
        print(f"   Type: {period.tariff_type.value.title()}")
        print(f"   Product: {period.product_code}")
        print(f"   Rates: {len(period.rates)} loaded")
        if period.notes:
            print(f"   Notes: {period.notes}")
        print()
    
    if not manager.config.import_timeline.periods:
        print("No import periods configured.")
    
    print("\nExport Timeline:")
    print("=" * 50)
    
    for i, period in enumerate(manager.config.export_timeline.periods):
        status = "ACTIVE" if period.is_active else "INACTIVE"
        end_str = period.end_date.strftime('%Y-%m-%d') if period.end_date else "Ongoing"
        
        print(f"{i+1}. {period.display_name}")
        print(f"   {period.start_date} - {end_str} [{status}]")
        print(f"   Type: {period.tariff_type.value.title()}")
        print(f"   Product: {period.product_code}")
        print(f"   Rates: {len(period.rates)} loaded")
        if period.notes:
            print(f"   Notes: {period.notes}")
        print()
    
    if not manager.config.export_timeline.periods:
        print("No export periods configured.")


def refresh_rates(manager):
    """Refresh rates for all periods."""
    print("Refreshing rates for all periods...")
    
    print("\nImport timeline:")
    for period in manager.config.import_timeline.periods:
        print(f"  Fetching rates for {period.display_name}...")
        manager.fetch_rates_for_period(period)
        print(f"    Loaded {len(period.rates)} rates")
    
    print("\nExport timeline:")
    for period in manager.config.export_timeline.periods:
        print(f"  Fetching rates for {period.display_name}...")
        manager.fetch_rates_for_period(period)
        print(f"    Loaded {len(period.rates)} rates")
    
    manager.save_config()
    print("\nRate refresh complete!")


def show_status(manager):
    """Show timeline status and validation."""
    summary = manager.get_timeline_summary()
    
    print("Tariff Timeline Status")
    print("=" * 30)
    print(f"Import periods: {summary['import_periods']}")
    print(f"Export periods: {summary['export_periods']}")
    print(f"Active import: {summary['import_active'] or 'None'}")
    print(f"Active export: {summary['export_active'] or 'None'}")
    
    validation = summary['validation']
    
    print("\nValidation Results:")
    print("-" * 20)
    
    # Import timeline validation
    import_issues = validation['import']
    print(f"Import timeline:")
    if import_issues['gaps']:
        print(f"  Gaps: {len(import_issues['gaps'])}")
    if import_issues['overlaps']:
        print(f"  Overlaps: {len(import_issues['overlaps'])}")
    if import_issues['invalid_periods']:
        print(f"  Invalid periods: {len(import_issues['invalid_periods'])}")
    
    if not any(import_issues.values()):
        print("  ✓ No issues found")
    
    # Export timeline validation
    export_issues = validation['export']
    print(f"Export timeline:")
    if export_issues['gaps']:
        print(f"  Gaps: {len(export_issues['gaps'])}")
    if export_issues['overlaps']:
        print(f"  Overlaps: {len(export_issues['overlaps'])}")
    if export_issues['invalid_periods']:
        print(f"  Invalid periods: {len(export_issues['invalid_periods'])}")
    
    if not any(export_issues.values()):
        print("  ✓ No issues found")


def lookup_rate(manager, args):
    """Look up rate for a specific datetime."""
    try:
        dt = datetime.fromisoformat(args.datetime)
        flow_direction = FlowDirection(args.flow)
        
        rate = manager.get_rate_at_datetime(dt, flow_direction)  # Auto-detect rate type
        
        if rate is None:
            print(f"No rate found for {args.datetime} ({args.flow})")
        else:
            print(f"Rate for {args.datetime}:")
            print(f"  Flow: {args.flow}")
            print(f"  Type: {rate.rate_type} (auto-detected)")
            print(f"  Rate: {rate.value_inc_vat:.4f} pence/kWh (inc VAT)")
        
    except Exception as e:
        print(f"Error looking up rate: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
