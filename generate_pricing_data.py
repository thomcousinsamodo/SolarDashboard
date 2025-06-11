#!/usr/bin/env python3
"""
Generate half-hourly pricing data from tariff configuration.
Creates pricing_raw.csv with all available rate data for fast chart generation.
Uses the same proven rate lookup logic as the dashboard.
"""

import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
import sys
import logging

# Import tariff tracker
try:
    from tariff_tracker.timeline_manager import TimelineManager
    from tariff_tracker.models import FlowDirection
    from zoneinfo import ZoneInfo
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure tariff_tracker is available and you're using Python 3.9+")
    sys.exit(1)

def get_data_range_from_config(mgr):
    """Get the actual data range from the configuration by checking rate availability."""
    print("🔍 Analyzing available rate data...")
    
    # Find the earliest start date and latest rate date across all periods
    earliest_start = None
    latest_rate_date = None
    
    for timeline in [mgr.config.import_timeline, mgr.config.export_timeline]:
        for period in timeline.periods:
            # Track earliest start date
            if earliest_start is None or period.start_date < earliest_start:
                earliest_start = period.start_date
            
            # Check the latest rate date in this period
            if period.rates:
                for rate in period.rates:
                    rate_date = rate.valid_from.date()
                    if latest_rate_date is None or rate_date > latest_rate_date:
                        latest_rate_date = rate_date
    
    # Default to today if no rates found
    if latest_rate_date is None:
        latest_rate_date = date.today()
    
    print(f"📅 Detected data range: {earliest_start} to {latest_rate_date}")
    return earliest_start, latest_rate_date

def generate_half_hourly_data(mgr, start_date, end_date):
    """Generate half-hourly rate data using the proven dashboard rate lookup logic."""
    print(f"⏱️  Generating 30-minute intervals from {start_date} to {end_date}...")
    
    # Create UK timezone-aware datetime range
    uk_tz = ZoneInfo('Europe/London') 
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=uk_tz)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=uk_tz)
    
    # Generate all 30-minute intervals
    intervals = []
    current_dt = start_datetime
    while current_dt <= end_datetime:
        intervals.append(current_dt)
        current_dt += timedelta(minutes=30)
    
    print(f"📈 Generated {len(intervals):,} half-hourly intervals")
    
    # Process rates for each flow direction
    all_data = []
    
    for flow_direction in [FlowDirection.IMPORT, FlowDirection.EXPORT]:
        flow_name = flow_direction.value
        print(f"\n🔍 Processing {flow_name} rates...")
        
        timeline = mgr.config.import_timeline if flow_direction == FlowDirection.IMPORT else mgr.config.export_timeline
        
        if not timeline.periods:
            print(f"⚠️  No {flow_name} periods configured")
            continue
        
        rates_found = 0
        
        for i, dt in enumerate(intervals):
            # Progress update every 10,000 intervals to reduce output
            if i > 0 and i % 10000 == 0:
                print(f"   Progress: {i:,}/{len(intervals):,} ({i/len(intervals)*100:.1f}%) - Found {rates_found:,} rates")
            
            try:
                # Use the same proven rate lookup logic as the dashboard
                rate = mgr.get_rate_at_datetime(dt, flow_direction)
                
                if rate:
                    # Find the period this belongs to for context
                    period = timeline.get_period_at_date(dt.date())
                    period_name = period.display_name if period else "Unknown"
                    
                    all_data.append({
                        'datetime': dt,
                        'flow_direction': flow_name,
                        'rate_exc_vat': rate.value_exc_vat,
                        'rate_inc_vat': rate.value_inc_vat,
                        'rate_type': rate.rate_type,
                        'period_name': period_name
                    })
                    rates_found += 1
                else:
                    # No rate found - include as gap
                    all_data.append({
                        'datetime': dt,
                        'flow_direction': flow_name,
                        'rate_exc_vat': None,
                        'rate_inc_vat': None,
                        'rate_type': None,
                        'period_name': None
                    })
                    
            except Exception as e:
                print(f"⚠️  Error processing {dt}: {e}")
                # Include as gap
                all_data.append({
                    'datetime': dt,
                    'flow_direction': flow_name,
                    'rate_exc_vat': None,
                    'rate_inc_vat': None,
                    'rate_type': None,
                    'period_name': None
                })
        
        print(f"✅ {flow_name}: {rates_found:,} rates found out of {len(intervals):,} intervals")
    
    return all_data

def generate_pricing_data(output_file='pricing_raw.csv'):
    """Generate comprehensive pricing data using proven dashboard logic."""
    print("🔄 Initializing tariff manager...")
    
    try:
        mgr = TimelineManager()
    except Exception as e:
        print(f"❌ Error initializing tariff manager: {e}")
        return False
    
    # Temporarily reduce logging verbosity for bulk operations
    original_log_levels = {}
    loggers_to_quiet = [
        'tariff_tracker.timeline',
        'tariff_tracker.api', 
        'tariff_tracker'
    ]
    
    print("🔇 Reducing log verbosity for bulk operations...")
    for logger_name in loggers_to_quiet:
        logger = logging.getLogger(logger_name)
        original_log_levels[logger_name] = logger.level
        logger.setLevel(logging.WARNING)  # Only warnings and errors
    
    try:
        # Get the actual data range from configuration
        start_date, end_date = get_data_range_from_config(mgr)
        
        if not start_date:
            print("❌ No tariff periods found in configuration")
            return False
        
        # Generate the data using proven logic
        rate_data = generate_half_hourly_data(mgr, start_date, end_date)
        
        if not rate_data:
            print("❌ No rate data generated")
            return False
        
        # Create DataFrame
        print(f"\n💾 Creating DataFrame with {len(rate_data):,} records...")
        df = pd.DataFrame(rate_data)
        
        # Sort by datetime and flow direction
        df = df.sort_values(['datetime', 'flow_direction']).reset_index(drop=True)
        
        # Save to CSV
        print(f"💾 Saving to {output_file}...")
        df.to_csv(output_file, index=False)
        
        # Summary statistics
        print("\n📊 Summary Statistics:")
        print(f"   Total records: {len(df):,}")
        print(f"   Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        
        for flow in ['import', 'export']:
            flow_data = df[df['flow_direction'] == flow]
            valid_rates = flow_data.dropna(subset=['rate_inc_vat'])
            print(f"   {flow.title()} records: {len(flow_data):,}")
            print(f"   {flow.title()} with rates: {len(valid_rates):,}")
            if len(valid_rates) > 0:
                print(f"   {flow.title()} rate range: {valid_rates['rate_inc_vat'].min():.3f}p to {valid_rates['rate_inc_vat'].max():.3f}p")
        
        gaps = len(df[df['rate_inc_vat'].isna()])
        print(f"   Records with gaps: {gaps:,}")
        
        print(f"\n✅ Pricing data successfully saved to {output_file}")
        return True
        
    finally:
        # Restore original logging levels
        print("🔊 Restoring original log levels...")
        for logger_name, original_level in original_log_levels.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(original_level)

def main():
    """Main function."""
    print("🐙 Octopus Energy Pricing Data Generator")
    print("Using proven dashboard rate lookup logic")
    print("=" * 50)
    
    # Check if output file exists
    output_file = 'pricing_raw.csv'
    if Path(output_file).exists():
        response = input(f"⚠️  {output_file} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            return
    
    start_time = datetime.now()
    success = generate_pricing_data(output_file)
    end_time = datetime.now()
    
    if success:
        duration = end_time - start_time
        print(f"\n🎉 Processing completed in {duration.total_seconds():.1f} seconds")
        print(f"📁 File size: {Path(output_file).stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("\n❌ Processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 