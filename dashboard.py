"""
Unified Octopus Energy Dashboard
Combines solar energy tracking and tariff management into a single web interface.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import plotly.graph_objs as go
import plotly.express as px
import plotly.utils
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import json
import os
from pathlib import Path
import database_utils
from credential_manager import CredentialManager

# Initialize credential manager
credential_manager = CredentialManager()

def get_api_credentials():
    """Get API credentials using secure credential manager."""
    try:
        # Try to get credentials silently first (using cached password if available)
        api_key, account_number = credential_manager.get_credentials(silent=True)
        
        if not api_key or not account_number:
            return None, None, 'API credentials not found or password required. Please run credential_manager.py to set up secure credentials or cache your password.'
        
        return api_key, account_number, None
        
    except Exception as e:
        return None, None, f'Error loading credentials: {str(e)}'

# Tariff tracker imports
try:
    from tariff_tracker.timeline_manager import TimelineManager
    from tariff_tracker.models import TariffType, FlowDirection
    from tariff_tracker.logging_config import get_logger, setup_logging
    TARIFF_AVAILABLE = True
except ImportError:
    print("⚠️  Tariff tracker not available")
    TARIFF_AVAILABLE = False

# Weather integration
try:
    from weather_integration import correlate_weather_solar, create_weather_solar_chart, get_weather_correlation_stats
    WEATHER_AVAILABLE = True
except ImportError:
    print("⚠️  Weather integration not available")
    WEATHER_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'unified-octopus-dashboard-secret-key'

# Initialize logging if available
if TARIFF_AVAILABLE:
    setup_logging(log_level="INFO")
    logger = get_logger('unified_dashboard')
    
    # Import the original tariff tracker routes to avoid code duplication
    from tariff_tracker.web_dashboard import get_manager as tariff_get_manager
    from tariff_tracker.web_dashboard import app as tariff_app
    
    # Use the original tariff manager
    def get_manager():
        return tariff_get_manager()
else:
    def get_manager():
        return None

# Solar data loading functions
def load_solar_data():
    """Load consumption data from database"""
    try:
        dataframes = {}
        
        # Load daily data
        daily_df = database_utils.load_consumption_data(table_name='consumption_daily')
        if not daily_df.empty:
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            daily_df = daily_df.sort_values('date').reset_index(drop=True)
        dataframes['daily'] = daily_df
        
        # Load raw data  
        raw_df = database_utils.load_consumption_data(table_name='consumption_raw')
        if not raw_df.empty:
            raw_df['interval_start'] = pd.to_datetime(raw_df['interval_start'])
            raw_df['interval_end'] = pd.to_datetime(raw_df['interval_end'])
            raw_df = raw_df.sort_values('interval_start').reset_index(drop=True)
        dataframes['raw'] = raw_df
        
        return dataframes
        
    except Exception as e:
        print(f"Warning: Error loading data from database: {e}")
        # Return empty dataframes as fallback
        return {
            'daily': pd.DataFrame(),
            'raw': pd.DataFrame()
        }

def calculate_summary_stats(df):
    """Calculate summary statistics for the dashboard"""
    if df.empty:
        return {
            'total_import': 0,
            'total_export': 0,
            'net_consumption': 0,
            'avg_daily_import': 0,
            'avg_daily_export': 0,
            'self_sufficiency': 0
        }
    
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    total_import = import_data['total_kwh'].sum() if not import_data.empty else 0
    total_export = export_data['total_kwh'].sum() if not export_data.empty else 0
    net_consumption = total_import - total_export
    
    avg_daily_import = import_data['total_kwh'].mean() if not import_data.empty else 0
    avg_daily_export = export_data['total_kwh'].mean() if not export_data.empty else 0
    
    return {
        'total_import': total_import,
        'total_export': total_export,
        'net_consumption': net_consumption,
        'avg_daily_import': avg_daily_import,
        'avg_daily_export': avg_daily_export,
        'self_sufficiency': (total_export / total_import * 100) if total_import > 0 else 0
    }

def get_temperature_data(df, use_rolling_avg=False):
    """Get temperature data for the same date range as energy data"""
    if df.empty or not WEATHER_AVAILABLE:
        return pd.DataFrame()
    
    try:
        from weather_integration import WeatherDataAPI
        
        start_date = df['date'].min()
        end_date = df['date'].max()
        
        weather_api = WeatherDataAPI()
        weather_df = weather_api.create_sample_weather_data(start_date, end_date)
        
        weather_df['date'] = pd.to_datetime(weather_df['date'])
        weather_df = weather_df.sort_values('date')
        
        if use_rolling_avg:
            date_range_days = (weather_df['date'].max() - weather_df['date'].min()).days
            
            if date_range_days < 90:
                window = 7
            elif date_range_days < 365:
                window = 14
            else:
                window = 30
                
            weather_df['temperature_avg_rolling'] = weather_df['temperature_avg'].rolling(window=window, center=True).mean()
            weather_df['sunshine_hours_rolling'] = weather_df['sunshine_hours'].rolling(window=window, center=True).mean()
        
        return weather_df
    except Exception as e:
        print(f"Error getting temperature data: {e}")
        return pd.DataFrame()

# Load solar data
solar_data = load_solar_data()
daily_df = solar_data['daily']
raw_df = solar_data['raw']

# Define color scheme
colors = {
    'background': '#f8f9fa',
    'primary': '#007bff',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'import': '#dc3545',  # Red for energy consumed
    'export': '#28a745'   # Green for energy generated
}

@app.route('/')
def index():
    """Main unified dashboard page."""
    # Check if credentials are accessible
    api_key, account_number, error_msg = get_api_credentials()
    credentials_available = api_key is not None and account_number is not None
    
    # Get solar stats with comparisons
    solar_stats = get_dashboard_solar_stats()
    
    # Get tariff summary if available
    tariff_summary = {}
    if TARIFF_AVAILABLE and credentials_available:
        try:
            mgr = get_manager()
            if mgr:
                tariff_summary = mgr.get_timeline_summary()
        except Exception as e:
            print(f"Error getting tariff summary: {e}")
            tariff_summary = {}
    
    # Check if solar data is available
    solar_data = load_solar_data()
    daily_df = solar_data['daily']
    solar_data_available = not daily_df.empty
    
    return render_template('index.html', 
                         solar_stats=solar_stats, 
                         tariff_summary=tariff_summary,
                         tariff_available=TARIFF_AVAILABLE,
                         solar_data_available=solar_data_available,
                         credentials_available=credentials_available,
                         credential_error=error_msg if not credentials_available else None)

def get_dashboard_solar_stats():
    """Get solar stats for the main dashboard with weekly focus and comparisons."""
    from datetime import datetime, timedelta
    import pandas as pd
    
    # Load solar data
    solar_data = load_solar_data()
    daily_df = solar_data['daily']
    
    if daily_df.empty:
        return create_empty_solar_stats()
    
    # Get date ranges
    today = datetime.now().date()
    
    # Current week (last 7 days)
    week_start = today - timedelta(days=6)  # 7 days including today
    week_start_pd = pd.to_datetime(week_start)
    current_week_df = daily_df[daily_df['date'] >= week_start_pd]
    
    # Previous week (7 days before current week)
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)
    prev_week_start_pd = pd.to_datetime(prev_week_start)
    prev_week_end_pd = pd.to_datetime(prev_week_end)
    prev_week_df = daily_df[
        (daily_df['date'] >= prev_week_start_pd) & 
        (daily_df['date'] <= prev_week_end_pd)
    ]
    
    # Previous month (30 days before current week)
    month_start = week_start - timedelta(days=30)
    month_end = week_start - timedelta(days=1)
    month_start_pd = pd.to_datetime(month_start)
    month_end_pd = pd.to_datetime(month_end)
    prev_month_df = daily_df[
        (daily_df['date'] >= month_start_pd) & 
        (daily_df['date'] <= month_end_pd)
    ]
    
    # Lifetime stats
    lifetime_df = daily_df
    
    # Calculate stats for each period
    current_stats = calculate_summary_stats(current_week_df) if not current_week_df.empty else create_empty_summary_stats()
    prev_week_stats = calculate_summary_stats(prev_week_df) if not prev_week_df.empty else create_empty_summary_stats()
    prev_month_stats = calculate_summary_stats(prev_month_df) if not prev_month_df.empty else create_empty_summary_stats()
    lifetime_stats = calculate_summary_stats(lifetime_df)
    
    # Calculate comparisons
    def calculate_comparison(current, previous):
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100
    
    # Week vs previous week
    import_week_change = calculate_comparison(
        current_stats['avg_daily_import'] if isinstance(current_stats, dict) else current_stats.avg_daily_import, 
        prev_week_stats['avg_daily_import'] if isinstance(prev_week_stats, dict) else prev_week_stats.avg_daily_import
    )
    export_week_change = calculate_comparison(
        current_stats['avg_daily_export'] if isinstance(current_stats, dict) else current_stats.avg_daily_export, 
        prev_week_stats['avg_daily_export'] if isinstance(prev_week_stats, dict) else prev_week_stats.avg_daily_export
    )
    
    # Week vs previous month daily average
    import_month_change = calculate_comparison(
        current_stats['avg_daily_import'] if isinstance(current_stats, dict) else current_stats.avg_daily_import, 
        prev_month_stats['avg_daily_import'] if isinstance(prev_month_stats, dict) else prev_month_stats.avg_daily_import
    )
    export_month_change = calculate_comparison(
        current_stats['avg_daily_export'] if isinstance(current_stats, dict) else current_stats.avg_daily_export, 
        prev_month_stats['avg_daily_export'] if isinstance(prev_month_stats, dict) else prev_month_stats.avg_daily_export
    )
    
    # Create enhanced stats object
    enhanced_stats = {
        # Current week totals
        'total_import': current_stats['total_import'] if isinstance(current_stats, dict) else current_stats.total_import,
        'total_export': current_stats['total_export'] if isinstance(current_stats, dict) else current_stats.total_export,
        'net_consumption': current_stats['net_consumption'] if isinstance(current_stats, dict) else current_stats.net_consumption,
        'self_sufficiency': current_stats['self_sufficiency'] if isinstance(current_stats, dict) else current_stats.self_sufficiency,
        'avg_daily_import': current_stats['avg_daily_import'] if isinstance(current_stats, dict) else current_stats.avg_daily_import,
        'avg_daily_export': current_stats['avg_daily_export'] if isinstance(current_stats, dict) else current_stats.avg_daily_export,
        
        # Comparisons
        'import_week_change': import_week_change,
        'export_week_change': export_week_change,
        'import_month_change': import_month_change,
        'export_month_change': export_month_change,
        
        # Period info
        'period_name': "Last 7 Days",
        'period_start': week_start.strftime('%b %d'),
        'period_end': today.strftime('%b %d'),
        'data_days': len(current_week_df),
        
        # Lifetime context
        'lifetime_total_import': lifetime_stats['total_import'] if isinstance(lifetime_stats, dict) else lifetime_stats.total_import,
        'lifetime_total_export': lifetime_stats['total_export'] if isinstance(lifetime_stats, dict) else lifetime_stats.total_export,
        'lifetime_avg_daily_import': lifetime_stats['avg_daily_import'] if isinstance(lifetime_stats, dict) else lifetime_stats.avg_daily_import,
        'lifetime_avg_daily_export': lifetime_stats['avg_daily_export'] if isinstance(lifetime_stats, dict) else lifetime_stats.avg_daily_export,
        
        # Data availability flags
        'has_prev_week': not prev_week_df.empty,
        'has_prev_month': not prev_month_df.empty,
        'has_current_data': not current_week_df.empty
    }
    
    return type('SolarStats', (), enhanced_stats)()

def create_empty_solar_stats():
    """Create empty solar stats when no data is available."""
    return type('SolarStats', (), {
        'total_import': 0,
        'total_export': 0,
        'net_consumption': 0,
        'self_sufficiency': 0,
        'avg_daily_import': 0,
        'avg_daily_export': 0,
        'import_week_change': 0,
        'export_week_change': 0,
        'import_month_change': 0,
        'export_month_change': 0,
        'period_name': "No Data",
        'period_start': "",
        'period_end': "",
        'data_days': 0,
        'lifetime_total_import': 0,
        'lifetime_total_export': 0,
        'lifetime_avg_daily_import': 0,
        'lifetime_avg_daily_export': 0,
        'has_prev_week': False,
        'has_prev_month': False,
        'has_current_data': False
    })()

def create_empty_summary_stats():
    """Create empty summary stats structure."""
    return type('SummaryStats', (), {
        'total_import': 0,
        'total_export': 0,
        'net_consumption': 0,
        'self_sufficiency': 0,
        'avg_daily_import': 0,
        'avg_daily_export': 0
    })()

@app.route('/solar')
def solar_dashboard():
    """Solar energy dashboard page."""
    # Load solar data and calculate stats
    solar_data = load_solar_data()
    daily_df = solar_data['daily']
    raw_df = solar_data['raw']
    solar_data_available = not daily_df.empty
    
    solar_stats = None
    data_min_date = None
    data_max_date = None
    
    if solar_data_available:
        solar_stats = calculate_summary_stats(daily_df)
        data_min_date = daily_df['date'].min().strftime('%Y-%m-%d')
        data_max_date = daily_df['date'].max().strftime('%Y-%m-%d')
    
    return render_template('solar.html',
                         data_available=solar_data_available,
                         solar_data_available=solar_data_available,
                         solar_stats=solar_stats,
                         data_min_date=data_min_date,
                         data_max_date=data_max_date,
                         tariff_available=TARIFF_AVAILABLE)

@app.route('/api/solar-chart', methods=['POST'])
def api_solar_chart():
    """API endpoint for generating solar charts."""
    try:
        data = request.get_json()
        chart_type = data.get('chart_type', 'daily_overview')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        options = data.get('options', [])
        
        # Filter data by date range if provided
        filtered_df = daily_df.copy()
        if start_date and end_date and not daily_df.empty:
            filtered_df = daily_df[
                (daily_df['date'] >= start_date) & 
                (daily_df['date'] <= end_date)
            ]
            
            # Check if filtered data is empty due to date range selection
            if filtered_df.empty:
                empty_message = f"No data available for selected date range<br>{start_date} to {end_date}"
                fig = create_empty_chart(empty_message)
                chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                return jsonify({'success': True, 'chart': chart_json})
        
        # Check if date range is more than 30 days for rolling averages
        date_range_days = 0
        if start_date and end_date:
            date_range_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
        elif not filtered_df.empty:
            date_range_days = (filtered_df['date'].max() - filtered_df['date'].min()).days
        
        # Generate chart based on type
        show_temperature = 'show_temperature' in options
        use_rolling_avg = 'use_rolling_avg' in options and date_range_days > 30
        
        if chart_type == 'daily_overview':
            fig = create_daily_overview_chart(filtered_df, show_temperature, use_rolling_avg)
        elif chart_type == 'hourly_analysis' and not raw_df.empty:
            fig = create_hourly_analysis_chart(raw_df, start_date, end_date)
        elif chart_type == 'net_flow':
            fig = create_net_flow_chart(filtered_df, show_temperature, use_rolling_avg)
        elif chart_type == 'energy_balance':
            fig = create_energy_balance_chart(filtered_df)
        elif chart_type == 'consumption_pattern':
            fig = create_consumption_pattern_chart(filtered_df, use_rolling_avg)
        else:
            fig = create_empty_chart("No data available")
        
        # Force Plotly to use regular arrays instead of binary encoding
        # This prevents frontend compatibility issues with binary data
        chart_dict = fig.to_dict()
        
        # Convert any binary encoded arrays to regular lists
        for trace in chart_dict.get('data', []):
            for key in ['x', 'y', 'z']:
                if key in trace and isinstance(trace[key], dict):
                    if 'dtype' in trace[key] and 'bdata' in trace[key]:
                        # Convert binary data back to regular array
                        import numpy as np
                        import base64
                        binary_data = base64.b64decode(trace[key]['bdata'])
                        dtype = trace[key]['dtype']
                        array = np.frombuffer(binary_data, dtype=dtype)
                        trace[key] = array.tolist()  # Convert to regular Python list
        
        chart_json = json.dumps(chart_dict, cls=plotly.utils.PlotlyJSONEncoder)
        return jsonify({'success': True, 'chart': chart_json})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/solar-summary', methods=['POST'])
def api_solar_summary():
    """API endpoint for getting solar summary stats for a date range."""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Load solar data
        solar_data = load_solar_data()
        daily_df = solar_data['daily']
        
        if daily_df.empty:
            return jsonify({'success': False, 'error': 'No solar data available'})
        
        # Filter data by date range if provided
        filtered_df = daily_df.copy()
        if start_date and end_date:
            filtered_df = daily_df[
                (daily_df['date'] >= start_date) & 
                (daily_df['date'] <= end_date)
            ]
        
        if filtered_df.empty:
            return jsonify({'success': False, 'error': 'No data available for selected date range'})
        
        # Calculate stats for filtered data
        solar_stats = calculate_summary_stats(filtered_df)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_import': round(solar_stats['total_import'], 1),
                'total_export': round(solar_stats['total_export'], 1),
                'net_consumption': round(solar_stats['net_consumption'], 1),
                'self_sufficiency': round(solar_stats['self_sufficiency'], 1),
                'avg_daily_import': round(solar_stats['avg_daily_import'], 1),
                'avg_daily_export': round(solar_stats['avg_daily_export'], 1),
                'generation_efficiency': round((solar_stats['total_export'] / (solar_stats['total_import'] + solar_stats['total_export'])) * 100 if (solar_stats['total_import'] + solar_stats['total_export']) > 0 else 0, 1)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# Tariff management routes (only if available)
if TARIFF_AVAILABLE:
    @app.route('/tariffs')
    def tariff_dashboard():
        """Tariff management dashboard page."""
        mgr = get_manager()
        summary = mgr.get_timeline_summary()
        validation = summary['validation']
        
        # Check if solar data is available for nav menu
        solar_data = load_solar_data()
        daily_df = solar_data['daily']
        solar_data_available = not daily_df.empty
        
        return render_template('tariffs.html', 
                             summary=summary,
                             validation=validation,
                             tariff_available=TARIFF_AVAILABLE,
                             solar_data_available=solar_data_available)

    @app.route('/periods')
    def periods():
        """View all tariff periods - using original tariff tracker functionality."""
        from tariff_tracker.web_dashboard import periods as original_periods
        return original_periods()

    # Import original tariff tracker routes to avoid code duplication
    @app.route('/add-period')
    def add_period_form():
        """Add period form page - using original tariff tracker functionality."""
        from tariff_tracker.web_dashboard import add_period_form as original_add_period_form
        return original_add_period_form()

    @app.route('/add-period', methods=['POST'])
    def add_period():
        """Handle add period form submission - using original tariff tracker functionality."""
        from tariff_tracker.web_dashboard import add_period as original_add_period
        return original_add_period()

    @app.route('/rate-lookup')
    def rate_lookup_form():
        """Rate lookup form page."""
        # Check if solar data is available for nav menu
        solar_data = load_solar_data()
        daily_df = solar_data['daily']
        solar_data_available = not daily_df.empty
        
        return render_template('rate_lookup.html',
                             tariff_available=TARIFF_AVAILABLE,
                             solar_data_available=solar_data_available)

    @app.route('/api/rate-lookup', methods=['POST'])
    def api_rate_lookup():
        """API endpoint for rate lookup."""
        try:
            from zoneinfo import ZoneInfo
            
            mgr = get_manager()
            
            datetime_str = request.json['datetime']
            flow_direction = FlowDirection(request.json['flow_direction'])
            
            dt = datetime.fromisoformat(datetime_str)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo('Europe/London'))
            
            rate = mgr.get_rate_at_datetime(dt, flow_direction)
            
            if rate:
                if flow_direction == FlowDirection.EXPORT:
                    return jsonify({
                        'success': True,
                        'rate': {
                            'value': rate.value_exc_vat,
                            'valid_from': rate.valid_from.isoformat(),
                            'valid_to': rate.valid_to.isoformat() if rate.valid_to else None,
                            'rate_type': rate.rate_type,
                            'is_export': True
                        }
                    })
                else:
                    return jsonify({
                        'success': True,
                        'rate': {
                            'value_inc_vat': rate.value_inc_vat,
                            'value_exc_vat': rate.value_exc_vat,
                            'valid_from': rate.valid_from.isoformat(),
                            'valid_to': rate.valid_to.isoformat() if rate.valid_to else None,
                            'rate_type': rate.rate_type,
                            'is_export': False
                        }
                    })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No rate found for the specified datetime'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
    
    # Add the API routes that the original tariff tracker needs
    @app.route('/api/available-tariffs')
    def api_available_tariffs():
        """API endpoint for available tariffs - using original functionality."""
        from tariff_tracker.web_dashboard import api_available_tariffs as original_api
        return original_api()
    
    @app.route('/api/delete-period', methods=['POST'])
    def api_delete_period():
        """API endpoint for deleting periods - using original functionality."""
        from tariff_tracker.web_dashboard import api_delete_period as original_api
        return original_api()
    
    @app.route('/api/refresh-rates', methods=['POST'])
    def api_refresh_rates():
        """API endpoint for refreshing rates - using original functionality."""
        from tariff_tracker.web_dashboard import api_refresh_rates as original_api
        return original_api()
    
    @app.route('/refresh-rates', methods=['POST'])
    def refresh_rates():
        """Refresh rates - using original functionality."""
        from tariff_tracker.web_dashboard import refresh_rates as original_refresh
        return original_refresh()
    
    @app.route('/api/rate-chart', methods=['POST'])
    def api_rate_chart():
        """API endpoint for generating rate charts."""
        try:
            data = request.get_json()
            chart_type = data.get('chart_type', 'timeline')
            start_date = data.get('start_date')
            end_date = data.get('end_date') 
            flow_direction = data.get('flow_direction', 'import')
            
            # Default to last 7 days if no dates provided
            if not start_date or not end_date:
                end_date = date.today()
                start_date = end_date - timedelta(days=7)
            
            # Get filtered pricing data from CSV
            rate_df = get_filtered_pricing_data(start_date, end_date, flow_direction)
            
            if rate_df.empty:
                fig = create_empty_rate_chart(f"No rate data available for {flow_direction} from {start_date} to {end_date}<br><br>💡 Run generate_pricing_data.py to create pricing data", flow_direction)
            else:
                fig = create_rate_timeline_chart(rate_df, chart_type, flow_direction)
            
            # Convert to JSON (same approach as solar charts)
            chart_dict = fig.to_dict()
            
            # Convert any binary encoded arrays to regular lists
            for trace in chart_dict.get('data', []):
                for key in ['x', 'y', 'z']:
                    if key in trace and isinstance(trace[key], dict):
                        if 'dtype' in trace[key] and 'bdata' in trace[key]:
                            import numpy as np
                            import base64
                            binary_data = base64.b64decode(trace[key]['bdata'])
                            dtype = trace[key]['dtype']
                            array = np.frombuffer(binary_data, dtype=dtype)
                            trace[key] = array.tolist()
            
            chart_json = json.dumps(chart_dict, cls=plotly.utils.PlotlyJSONEncoder)
            return jsonify({'success': True, 'chart': chart_json})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

# Chart creation functions (from solar dashboard)
def add_rolling_averages(df, window=7):
    """Add rolling averages to the dataframe"""
    df_copy = df.copy()
    df_copy = df_copy.sort_values('date')
    
    for meter_type in df_copy['meter_type'].unique():
        mask = df_copy['meter_type'] == meter_type
        df_copy.loc[mask, 'rolling_avg'] = df_copy.loc[mask, 'total_kwh'].rolling(window=window, center=True).mean()
    
    return df_copy

def create_daily_overview_chart(df, show_temperature=False, use_rolling_avg=False):
    """Create daily overview chart showing import vs export"""
    if df.empty:
        return create_empty_chart("No daily data available")
    
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    # Create figure with secondary y-axis if temperature is requested
    if show_temperature:
        from plotly.subplots import make_subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
    
    # Apply rolling averages if requested
    if use_rolling_avg:
        df_with_rolling = add_rolling_averages(df)
        import_data_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'import']
        export_data_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'export']
        
        # Add rolling average traces (primary y-axis)
        if not import_data_rolling.empty:
            fig.add_trace(go.Scatter(
                x=import_data_rolling['date'],
                y=import_data_rolling['rolling_avg'],
                mode='lines',
                name='Import (7-day avg)',
                line=dict(color=colors['import'], width=3),
                hovertemplate='<b>Import (7-day avg)</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
            ), secondary_y=False if show_temperature else None)
        
        if not export_data_rolling.empty:
            fig.add_trace(go.Scatter(
                x=export_data_rolling['date'],
                y=export_data_rolling['rolling_avg'],
                mode='lines',
                name='Export (7-day avg)',
                line=dict(color=colors['export'], width=3),
                hovertemplate='<b>Export (7-day avg)</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
            ), secondary_y=False if show_temperature else None)
        
        # Add original data as lighter traces
        if not import_data.empty:
            fig.add_trace(go.Scatter(
                x=import_data['date'],
                y=import_data['total_kwh'],
                mode='lines',
                name='Grid Import (daily)',
                line=dict(color=colors['import'], width=1, dash='dot'),
                opacity=0.4,
                hovertemplate='<b>Grid Import</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
            ), secondary_y=False if show_temperature else None)
        
        if not export_data.empty:
            fig.add_trace(go.Scatter(
                x=export_data['date'],
                y=export_data['total_kwh'],
                mode='lines',
                name='Solar Export (daily)',
                line=dict(color=colors['export'], width=1, dash='dot'),
                opacity=0.4,
                hovertemplate='<b>Solar Export</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
            ), secondary_y=False if show_temperature else None)
    else:
        # Add regular traces (primary y-axis) - WORKING VERSION FROM SOLAR_DASHBOARD.PY
        if not import_data.empty:
            fig.add_trace(go.Scatter(
                x=import_data['date'],
                y=import_data['total_kwh'],
                mode='lines+markers',
                name='Grid Import',
                line=dict(color=colors['import'], width=3),
                marker=dict(size=6),
                hovertemplate='<b>Grid Import</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
            ), secondary_y=False if show_temperature else None)
        
        if not export_data.empty:
            fig.add_trace(go.Scatter(
                x=export_data['date'],
                y=export_data['total_kwh'],
                mode='lines+markers',
                name='Solar Export',
                line=dict(color=colors['export'], width=3),
                marker=dict(size=6),
                hovertemplate='<b>Solar Export</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
            ), secondary_y=False if show_temperature else None)
    
    # Add temperature trace if requested
    if show_temperature:
        weather_df = get_temperature_data(df, use_rolling_avg)
        if not weather_df.empty:
            if use_rolling_avg and 'temperature_avg_rolling' in weather_df.columns:
                # Show both original and rolling average temperature
                fig.add_trace(go.Scatter(
                    x=weather_df['date'],
                    y=weather_df['temperature_avg'],
                    mode='lines',
                    name='Temperature (daily)',
                    line=dict(color='orange', width=1, dash='dot'),
                    opacity=0.4,
                    yaxis='y2',
                    hovertemplate='<b>Temperature (daily)</b><br>Date: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                ), secondary_y=True)
                
                fig.add_trace(go.Scatter(
                    x=weather_df['date'],
                    y=weather_df['temperature_avg_rolling'],
                    mode='lines',
                    name='Temperature (avg)',
                    line=dict(color='orange', width=2),
                    yaxis='y2',
                    hovertemplate='<b>Temperature (rolling avg)</b><br>Date: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                ), secondary_y=True)
            else:
                # Standard temperature line
                fig.add_trace(go.Scatter(
                    x=weather_df['date'],
                    y=weather_df['temperature_avg'],
                    mode='lines',
                    name='Temperature',
                    line=dict(color='orange', width=2),
                    yaxis='y2',
                    hovertemplate='<b>Temperature</b><br>Date: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                ), secondary_y=True)
            
            # Set y-axis titles
            fig.update_yaxes(title_text='Energy (kWh)', secondary_y=False)
            fig.update_yaxes(title_text='Temperature (°C)', secondary_y=True)
    
    # Update layout - WORKING VERSION FROM SOLAR_DASHBOARD.PY
    title = 'Daily Energy Import vs Export'
    if use_rolling_avg:
        title += ' (with 7-day Rolling Average)'
    if show_temperature:
        title += ' & Temperature'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Energy (kWh)' if not show_temperature else None,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_hourly_analysis_chart(df, start_date, end_date):
    """Create hourly analysis chart"""
    if df.empty:
        return create_empty_chart("No hourly data available")
    
    # Filter by date range if provided - WORKING VERSION FROM SOLAR_DASHBOARD.PY
    filtered_df = df.copy()
    if start_date and end_date:
        filtered_df = df[
            (df['interval_start'].dt.date >= pd.to_datetime(start_date).date()) &
            (df['interval_start'].dt.date <= pd.to_datetime(end_date).date())
        ]
    
    # Extract hour and calculate average consumption by hour - FIX PANDAS WARNING
    filtered_df = filtered_df.copy()  # Create explicit copy to avoid warning
    filtered_df['hour'] = filtered_df['interval_start'].dt.hour
    hourly_avg = filtered_df.groupby(['hour', 'meter_type'])['consumption'].mean().reset_index()
    
    import_hourly = hourly_avg[hourly_avg['meter_type'] == 'import']
    export_hourly = hourly_avg[hourly_avg['meter_type'] == 'export']
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=import_hourly['hour'],
        y=import_hourly['consumption'],
        name='Avg Import',
        marker_color=colors['import'],
        opacity=0.7
    ))
    
    fig.add_trace(go.Bar(
        x=export_hourly['hour'],
        y=export_hourly['consumption'],
        name='Avg Export',
        marker_color=colors['export'],
        opacity=0.7
    ))
    
    fig.update_layout(
        title='Average Hourly Energy Profile',
        xaxis_title='Hour of Day',
        yaxis_title='Average Energy (kWh)',
        template='plotly_white',
        barmode='group'
    )
    
    return fig

def create_net_flow_chart(df, show_temperature=False, use_rolling_avg=False):
    """Create net energy flow chart"""
    if df.empty:
        return create_empty_chart("No data available for net flow")
    
    # Calculate net flow (import - export) for each date
    pivot_df = df.pivot_table(
        index='date', 
        columns='meter_type', 
        values='total_kwh', 
        fill_value=0
    ).reset_index()
    
    if 'import' not in pivot_df.columns:
        pivot_df['import'] = 0
    if 'export' not in pivot_df.columns:
        pivot_df['export'] = 0
        
    pivot_df['net_flow'] = pivot_df['import'] - pivot_df['export']
    
    # Create figure with secondary y-axis if temperature is requested
    if show_temperature:
        from plotly.subplots import make_subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
    
    # Create colors based on positive/negative flow
    colors_net = ['red' if x > 0 else 'green' for x in pivot_df['net_flow']]
    
    # Add main net flow trace
    fig.add_trace(go.Bar(
        x=pivot_df['date'],
        y=pivot_df['net_flow'],
        marker_color=colors_net,
        name='Net Energy Flow',
        hovertemplate='<b>Net Flow</b><br>Date: %{x}<br>Net: %{y:.2f} kWh<br>' +
                     '<i>Positive = Grid Import, Negative = Solar Export</i><extra></extra>'
    ), secondary_y=False if show_temperature else None)
    
    # Add rolling average if requested
    if use_rolling_avg:
        pivot_df_sorted = pivot_df.sort_values('date')
        pivot_df_sorted['rolling_avg'] = pivot_df_sorted['net_flow'].rolling(window=7, center=True).mean()
        
        fig.add_trace(go.Scatter(
            x=pivot_df_sorted['date'],
            y=pivot_df_sorted['rolling_avg'],
            mode='lines',
            name='Net Flow (7-day avg)',
            line=dict(color='purple', width=3),
            hovertemplate='<b>Net Flow (7-day avg)</b><br>Date: %{x}<br>Net: %{y:.2f} kWh<extra></extra>'
        ), secondary_y=False if show_temperature else None)
    
    # Add temperature trace if requested
    if show_temperature:
        try:
            weather_df = get_temperature_data(df, use_rolling_avg)
            if not weather_df.empty:
                if use_rolling_avg and 'temperature_avg_rolling' in weather_df.columns:
                    # Show both original and rolling average temperature
                    fig.add_trace(go.Scatter(
                        x=weather_df['date'],
                        y=weather_df['temperature_avg'],
                        mode='lines',
                        name='Temperature (daily)',
                        line=dict(color='orange', width=1, dash='dot'),
                        opacity=0.4,
                        yaxis='y2',
                        hovertemplate='<b>Temperature (daily)</b><br>Date: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                    ), secondary_y=True)
                    
                    fig.add_trace(go.Scatter(
                        x=weather_df['date'],
                        y=weather_df['temperature_avg_rolling'],
                        mode='lines',
                        name='Temperature (avg)',
                        line=dict(color='orange', width=2),
                        yaxis='y2',
                        hovertemplate='<b>Temperature (rolling avg)</b><br>Date: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                    ), secondary_y=True)
                else:
                    # Standard temperature line
                    fig.add_trace(go.Scatter(
                        x=weather_df['date'],
                        y=weather_df['temperature_avg'],
                        mode='lines',
                        name='Temperature',
                        line=dict(color='orange', width=2),
                        yaxis='y2',
                        hovertemplate='<b>Temperature</b><br>Date: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
                    ), secondary_y=True)
                
                # Set y-axis titles
                fig.update_yaxes(title_text='Net Energy (kWh)', secondary_y=False)
                fig.update_yaxes(title_text='Temperature (°C)', secondary_y=True)
        except Exception as e:
            print(f"Temperature data not available: {e}")
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    
    # Update layout
    title = 'Net Energy Flow (Import - Export)'
    if use_rolling_avg:
        title += ' (with 7-day Rolling Average)'
    if show_temperature:
        title += ' & Temperature'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Net Energy (kWh)' if not show_temperature else None,
        template='plotly_white',
        annotations=[
            dict(
                x=0.02, y=0.98,
                xref='paper', yref='paper',
                text='🔴 Above zero: Net consumption<br>🟢 Below zero: Net generation',
                showarrow=False,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='gray',
                borderwidth=1
            )
        ]
    )
    
    return fig

def create_energy_balance_chart(df):
    """Create energy balance pie chart"""
    if df.empty:
        return create_empty_chart("No data available")
    
    import_total = df[df['meter_type'] == 'import']['total_kwh'].sum()
    export_total = df[df['meter_type'] == 'export']['total_kwh'].sum()
    
    fig = go.Figure(data=[go.Pie(
        labels=['Grid Import', 'Solar Export'],
        values=[import_total, export_total],
        hole=0.4,
        marker_colors=[colors['import'], colors['export']],
        hovertemplate='<b>%{label}</b><br>Energy: %{value:.1f} kWh<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title='Energy Balance Overview',
        template='plotly_white',
        annotations=[dict(text=f'{import_total + export_total:.1f}<br>Total kWh', 
                         x=0.5, y=0.5, font_size=14, showarrow=False)]
    )
    
    return fig

def create_consumption_pattern_chart(df, use_rolling_avg=False):
    """Create consumption pattern chart showing trends"""
    if df.empty:
        return create_empty_chart("No data available")
    
    # Calculate rolling window based on data range
    date_range_days = (df['date'].max() - df['date'].min()).days if not df.empty else 0
    
    # Adaptive rolling window: 7 days for < 90 days, 14 days for 90-365 days, 30 days for > 365 days
    if date_range_days < 90:
        window = 7
    elif date_range_days < 365:
        window = 14
    else:
        window = 30
    
    # Sort data by date
    df_sorted = df.sort_values('date')
    import_df = df_sorted[df_sorted['meter_type'] == 'import'].copy()
    export_df = df_sorted[df_sorted['meter_type'] == 'export'].copy()
    
    fig = go.Figure()
    
    if use_rolling_avg:
        # Use custom rolling averages for longer periods
        if not import_df.empty:
            import_df['rolling_avg'] = import_df['total_kwh'].rolling(window=window, center=True).mean()
            
            # Show both original data (lighter) and rolling average (bold)
            fig.add_trace(go.Scatter(
                x=import_df['date'],
                y=import_df['total_kwh'],
                mode='lines',
                name='Import (daily)',
                line=dict(color=colors['import'], width=1),
                opacity=0.3
            ))
            
            fig.add_trace(go.Scatter(
                x=import_df['date'],
                y=import_df['rolling_avg'],
                mode='lines',
                name=f'Import ({window}-day avg)',
                line=dict(color=colors['import'], width=3)
            ))
        
        if not export_df.empty:
            export_df['rolling_avg'] = export_df['total_kwh'].rolling(window=window, center=True).mean()
            
            # Show both original data (lighter) and rolling average (bold)
            fig.add_trace(go.Scatter(
                x=export_df['date'],
                y=export_df['total_kwh'],
                mode='lines',
                name='Export (daily)',
                line=dict(color=colors['export'], width=1),
                opacity=0.3
            ))
            
            fig.add_trace(go.Scatter(
                x=export_df['date'],
                y=export_df['rolling_avg'],
                mode='lines',
                name=f'Export ({window}-day avg)',
                line=dict(color=colors['export'], width=3)
            ))
        
        title = f'Energy Consumption Trends ({window}-day Rolling Average)'
        yaxis_title = f'{window}-day Average (kWh)'
    else:
        # Standard trend lines (7-day rolling average)
        if not import_df.empty:
            import_df['rolling_avg'] = import_df['total_kwh'].rolling(window=7, center=True).mean()
            fig.add_trace(go.Scatter(
                x=import_df['date'],
                y=import_df['rolling_avg'],
                mode='lines',
                name='Import Trend (7-day avg)',
                line=dict(color=colors['import'], width=2, dash='dash')
            ))
        
        if not export_df.empty:
            export_df['rolling_avg'] = export_df['total_kwh'].rolling(window=7, center=True).mean()
            fig.add_trace(go.Scatter(
                x=export_df['date'],
                y=export_df['rolling_avg'],
                mode='lines',
                name='Export Trend (7-day avg)',
                line=dict(color=colors['export'], width=2, dash='dash')
            ))
        
        title = 'Energy Consumption Trends'
        yaxis_title = '7-day Average (kWh)'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title=yaxis_title,
        template='plotly_white'
    )
    
    return fig

def load_pricing_data():
    """Load pricing data from database."""
    try:
        df = database_utils.load_pricing_data()
        if not df.empty:
            # Check if we have the old format (valid_from) or new format (datetime)
            if 'valid_from' in df.columns:
                # Old format from CSV migration
                df['datetime'] = pd.to_datetime(df['valid_from'], utc=True)
                df['rate_inc_vat'] = df['value_inc_vat']
                df['rate_exc_vat'] = df['value_exc_vat']
            else:
                # New format from generate_pricing_data.py
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
                # rate_inc_vat and rate_exc_vat columns already exist
            
            df = df.sort_values(['datetime', 'flow_direction']).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Warning: Error loading pricing data from database: {e}")
        print("Make sure the database has been created with migrate_to_database.py")
        return pd.DataFrame()

def load_standing_charges():
    """Load standing charges from tariff configuration."""
    try:
        with open('tariff_config.json', 'r') as f:
            config = json.load(f)
        
        standing_charges = []
        
        # Process import timeline for standing charges
        if 'import_timeline' in config and 'periods' in config['import_timeline']:
            for period in config['import_timeline']['periods']:
                if 'standing_charges' in period and period['standing_charges']:
                    for charge in period['standing_charges']:
                        standing_charges.append({
                            'valid_from': charge['valid_from'],
                            'valid_to': charge['valid_to'],
                            'value_exc_vat': charge['value_exc_vat'],
                            'value_inc_vat': charge['value_inc_vat'],
                            'period_name': period.get('display_name', ''),
                            'start_date': period['start_date'],
                            'end_date': period['end_date']
                        })
        
        df = pd.DataFrame(standing_charges)
        if not df.empty:
            # Convert to datetime
            df['valid_from'] = pd.to_datetime(df['valid_from'])
            df['valid_to'] = pd.to_datetime(df['valid_to'])
            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])
            
        return df
        
    except Exception as e:
        print(f"Error loading standing charges: {e}")
        return pd.DataFrame()

def get_standing_charge_for_date(date, standing_charges_df):
    """Get the standing charge that applies to a specific date."""
    if standing_charges_df.empty:
        return 0.0

    # Convert date to pandas datetime for comparison
    if hasattr(date, 'date'):  # It's already a datetime/timestamp
        target_date = pd.to_datetime(date.date())
    else:  # It's a date object
        target_date = pd.to_datetime(date)

    # Convert DataFrame date columns to date for comparison
    start_dates = pd.to_datetime(standing_charges_df['start_date'].dt.date)
    end_dates = pd.to_datetime(standing_charges_df['end_date'].dt.date)

    # Find the standing charge period that covers this date
    # Handle ongoing periods where end_date is null
    applicable = standing_charges_df[
        (start_dates <= target_date) & 
        ((end_dates >= target_date) | pd.isna(standing_charges_df['end_date']))
    ]

    if not applicable.empty:
        return applicable.iloc[0]['value_inc_vat']  # Return in pence for consistency with rates

    return 0.0

def get_filtered_pricing_data(start_date, end_date, flow_direction='import'):
    """Get filtered pricing data for the specified date range and flow direction.
    
    Args:
        start_date: Start date (string or date object)
        end_date: End date (string or date object) 
        flow_direction: 'import' or 'export'
        
    Returns:
        pandas.DataFrame with filtered pricing data
    """
    # Load full pricing dataset
    df = load_pricing_data()
    
    if df.empty:
        return pd.DataFrame()
        
    try:
        # Convert dates to timezone-aware datetime objects for proper comparison
        from datetime import date
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date, utc=True)
        elif isinstance(start_date, date):  # It's a date object
            start_date = pd.to_datetime(start_date).tz_localize('UTC')
            
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date, utc=True)
        elif isinstance(end_date, date):  # It's a date object
            end_date = pd.to_datetime(end_date).tz_localize('UTC')
            
        # Ensure end_date includes the full day (only for datetime objects, not date objects)
        if hasattr(end_date, 'time') and end_date.time() == pd.Timestamp('00:00:00').time():
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
        # Filter by date range and flow direction
        mask = (
            (df['datetime'] >= start_date) & 
            (df['datetime'] <= end_date) &
            (df['flow_direction'] == flow_direction)
        )
        
        filtered_df = df[mask].copy()
        print(f"Debug: Filtered {len(filtered_df)} records for {flow_direction} from {start_date} to {end_date}")
        return filtered_df.reset_index(drop=True)
        
    except Exception as e:
        print(f"Error filtering pricing data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def create_empty_rate_chart(message, flow_direction='import'):
    """Create an empty rate chart with a message and pricing data availability info"""
    fig = go.Figure()
    
    # Get pricing data availability info
    data_range_info = ""
    try:
        pricing_df = load_pricing_data()
        if not pricing_df.empty:
            # Filter for the specific flow direction and remove NaN rates
            flow_data = pricing_df[pricing_df['flow_direction'] == flow_direction].dropna(subset=['rate_inc_vat'])
            if not flow_data.empty:
                min_date = flow_data['datetime'].min().strftime('%Y-%m-%d')
                max_date = flow_data['datetime'].max().strftime('%Y-%m-%d')
                data_range_info = f"<br><br>📅 {flow_direction.title()} data available: {min_date} to {max_date}"
    except:
        pass
    
    fig.add_annotation(
        text=f"{message}{data_range_info}",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        xanchor='center', yanchor='middle',
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        template='plotly_white',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        height=500
    )
    return fig

def create_rate_timeline_chart(rate_df, chart_type='timeline', flow_direction='import'):
    """Create a chart showing rates over time.
    
    Args:
        rate_df: DataFrame with rate data from get_filtered_pricing_data
        chart_type: 'timeline', 'daily_avg', or 'period_comparison'
        flow_direction: 'import' or 'export' for better error messages
    """
    if rate_df.empty:
        return create_empty_rate_chart("No rate data available for selected period", flow_direction)
        
    fig = go.Figure()
    
    if chart_type == 'timeline':
        # Remove gaps (None values) for cleaner display
        valid_data = rate_df.dropna(subset=['rate_inc_vat'])
        
        if valid_data.empty:
            return create_empty_rate_chart("No valid rate data found for selected period", flow_direction)
        
        # Calculate the time period in days
        if not valid_data.empty:
            date_range = (valid_data['datetime'].max() - valid_data['datetime'].min()).days
            
            # Auto-switch to daily averages for large time periods to prevent solid block appearance
            if date_range > 90:  # More than 3 months
                print(f"Large time period detected ({date_range} days) - using daily averages for better visibility")
                
                # Calculate daily averages
                daily_avg = valid_data.groupby(valid_data['datetime'].dt.date).agg({
                    'rate_inc_vat': ['mean', 'min', 'max'],
                    'rate_exc_vat': 'mean'
                }).round(3)
                
                # Flatten column names
                daily_avg.columns = ['avg_rate_inc_vat', 'min_rate_inc_vat', 'max_rate_inc_vat', 'avg_rate_exc_vat']
                daily_avg = daily_avg.reset_index()
                daily_avg = daily_avg.dropna(subset=['avg_rate_inc_vat'])
                
                if daily_avg.empty:
                    return create_empty_rate_chart("No daily average data available for selected period", flow_direction)
                
                # Add min/max range as fill
                fig.add_trace(go.Scatter(
                    x=daily_avg['datetime'],
                    y=daily_avg['max_rate_inc_vat'],
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                fig.add_trace(go.Scatter(
                    x=daily_avg['datetime'],
                    y=daily_avg['min_rate_inc_vat'],
                    mode='lines',
                    line=dict(width=0),
                    fillcolor='rgba(54, 162, 235, 0.2)',
                    fill='tonexty',
                    name='Daily Range',
                    hovertemplate='Min: %{y:.2f}p/kWh<br>%{x}<extra></extra>'
                ))
                
                # Add average line on top
                fig.add_trace(go.Scatter(
                    x=daily_avg['datetime'],
                    y=daily_avg['avg_rate_inc_vat'],
                    mode='lines',
                    name='Daily Average (inc VAT)',
                    line=dict(color=colors['primary'], width=2),
                    hovertemplate='<b>%{y:.2f}p/kWh</b> (daily avg)<br>%{x}<br><extra></extra>'
                ))
                
                title = f'Electricity Rates Over Time (Daily Averages - {date_range} days)'
                xaxis_title = 'Date'
                
            else:
                # Use half-hourly data for shorter periods
                fig.add_trace(go.Scatter(
                    x=valid_data['datetime'],
                    y=valid_data['rate_inc_vat'],
                    mode='lines',
                    name='Rate (inc VAT)',
                    line=dict(color=colors['primary'], width=1),
                    hovertemplate='<b>%{y:.2f}p/kWh</b><br>%{x}<br><extra></extra>'
                ))
                
                title = f'Electricity Rates Over Time (Half-hourly - {date_range} days)'
                xaxis_title = 'Date & Time'
        
        # Add standing charges baseline for import rates only
        if flow_direction == 'import':
            try:
                standing_charges_df = load_standing_charges()
                if not standing_charges_df.empty:
                    # Create standing charge data for the time period
                    if date_range > 90:
                        # For daily averages, show daily standing charge
                        daily_standing_charges = []
                        for _, row in daily_avg.iterrows():
                            # daily_avg has 'datetime' column which is actually a date
                            date_val = row['datetime']
                            if hasattr(date_val, 'date'):
                                date_val = date_val.date()
                            charge = get_standing_charge_for_date(date_val, standing_charges_df)
                            daily_standing_charges.append(charge)
                        
                        if any(c > 0 for c in daily_standing_charges):
                            fig.add_trace(go.Scatter(
                                x=daily_avg['datetime'],
                                y=daily_standing_charges,
                                mode='lines',
                                name='Daily Standing Charge',
                                line=dict(color='#ffc107', width=2),
                                hovertemplate='<b>Standing Charge:</b> %{y:.2f}p/day<br>%{x}<br><extra></extra>'
                            ))
                    else:
                        # For half-hourly data, show continuous standing charge line
                        if not valid_data.empty:
                            # Get standing charge for the date range - create daily points for continuous line
                            start_date = valid_data['datetime'].min()
                            end_date = valid_data['datetime'].max()
                            
                            # Create daily points to show standing charges properly
                            daily_dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq='D')
                            standing_charges = []
                            standing_dates = []
                            
                            for date in daily_dates:
                                charge = get_standing_charge_for_date(date.date(), standing_charges_df)
                                standing_charges.append(charge)
                                standing_dates.append(date)
                            
                            if standing_charges and any(c > 0 for c in standing_charges):
                                # Create a continuous line showing the standing charge level for each day
                                fig.add_trace(go.Scatter(
                                    x=standing_dates,
                                    y=standing_charges,
                                    mode='lines',
                                    name='Daily Standing Charge',
                                    line=dict(color='#ffc107', width=2),
                                    hovertemplate='<b>Standing Charge:</b> %{y:.2f}p/day<br>%{x}<br><extra></extra>'
                                ))
            except Exception as e:
                print(f"Warning: Could not add standing charges to chart: {e}")
        
        fig.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Rate (pence/kWh)',
            height=500
        )
        
    elif chart_type == 'daily_avg':
        # Daily average rates
        daily_avg = rate_df.groupby(rate_df['datetime'].dt.date).agg({
            'rate_inc_vat': 'mean',
            'rate_exc_vat': 'mean'
        }).reset_index()
        daily_avg.columns = ['date', 'avg_rate_inc_vat', 'avg_rate_exc_vat']
        
        # Filter out NaN values
        daily_avg = daily_avg.dropna(subset=['avg_rate_inc_vat'])
        
        if daily_avg.empty:
            return create_empty_rate_chart("No daily average data available for selected period", flow_direction)
        
        fig.add_trace(go.Scatter(
            x=daily_avg['date'],
            y=daily_avg['avg_rate_inc_vat'],
            mode='lines+markers',
            name='Daily Average (inc VAT)',
            line=dict(color=colors['primary'], width=2),
            marker=dict(size=6),
            hovertemplate='<b>%{y:.2f}p/kWh</b><br>%{x}<br><extra></extra>'
        ))
        
        # Add standing charges for import rates only
        if flow_direction == 'import':
            try:
                standing_charges_df = load_standing_charges()
                if not standing_charges_df.empty:
                    daily_standing_charges = []
                    for _, row in daily_avg.iterrows():
                        charge = get_standing_charge_for_date(row['date'], standing_charges_df)
                        daily_standing_charges.append(charge)
                    
                    if any(c > 0 for c in daily_standing_charges):
                        fig.add_trace(go.Scatter(
                            x=daily_avg['date'],
                            y=daily_standing_charges,
                            mode='lines+markers',
                            name='Daily Standing Charge',
                            line=dict(color='#ffc107', width=2),
                            marker=dict(size=4),
                            hovertemplate='<b>Standing Charge:</b> %{y:.2f}p/day<br>%{x}<br><extra></extra>'
                        ))
            except Exception as e:
                print(f"Warning: Could not add standing charges to daily avg chart: {e}")
        
        fig.update_layout(
            title='Daily Average Electricity Rates',
            xaxis_title='Date',
            yaxis_title='Average Rate (pence/kWh)',
            height=500
        )
        
    elif chart_type == 'period_comparison':
        # Compare rates by tariff period
        period_stats = rate_df.groupby('period_name').agg({
            'rate_inc_vat': ['mean', 'min', 'max', 'std']
        }).round(3)
        
        period_stats.columns = ['avg_rate', 'min_rate', 'max_rate', 'std_rate']
        period_stats = period_stats.reset_index()
        period_stats = period_stats.dropna()
        
        if period_stats.empty:
            return create_empty_rate_chart("No period data available for comparison", flow_direction)
            
        fig.add_trace(go.Bar(
            x=period_stats['period_name'],
            y=period_stats['avg_rate'],
            name='Average Rate',
            marker_color=colors['primary'],
            error_y=dict(
                type='data',
                symmetric=False,
                array=period_stats['max_rate'] - period_stats['avg_rate'],
                arrayminus=period_stats['avg_rate'] - period_stats['min_rate']
            ),
            hovertemplate='<b>%{y:.2f}p/kWh</b><br>Min: %{customdata[0]:.2f}p<br>Max: %{customdata[1]:.2f}p<br>Std: %{customdata[2]:.2f}p<extra></extra>',
            customdata=period_stats[['min_rate', 'max_rate', 'std_rate']].values
        ))
        
        fig.update_layout(
            title='Rate Statistics by Tariff Period',
            xaxis_title='Tariff Period',
            yaxis_title='Rate (pence/kWh)',
            height=500
        )
    
    # Common layout updates
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=60, r=30, t=60, b=40),
        hovermode='x unified'
    )
    
    fig.update_xaxes(gridcolor='lightgray', gridwidth=1)
    fig.update_yaxes(gridcolor='lightgray', gridwidth=1)
    
    return fig

def create_empty_chart(message):
    """Create an empty chart with a message"""
    fig = go.Figure()
    
    data_range_info = ""
    if not daily_df.empty:
        min_date = daily_df['date'].min().strftime('%Y-%m-%d')
        max_date = daily_df['date'].max().strftime('%Y-%m-%d')
        data_range_info = f"<br><br>📅 Data available: {min_date} to {max_date}"
    
    fig.add_annotation(
        text=f"{message}{data_range_info}",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        xanchor='center', yanchor='middle',
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        template='plotly_white',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False)
    )
    return fig

@app.route('/api/solar-charts-all', methods=['POST'])
def api_solar_charts_all():
    """API endpoint for generating all solar charts at once."""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        options = data.get('options', [])
        
        # Load solar data
        solar_data = load_solar_data()
        daily_df = solar_data['daily']
        raw_df = solar_data['raw']
        
        if daily_df.empty:
            return jsonify({'success': False, 'error': 'No solar data available'})
        
        # Filter data by date range if provided
        filtered_df = daily_df.copy()
        if start_date and end_date:
            filtered_df = daily_df[
                (daily_df['date'] >= start_date) & 
                (daily_df['date'] <= end_date)
            ]
            
            # Check if filtered data is empty due to date range selection
            if filtered_df.empty:
                empty_message = f"No data available for selected date range<br>{start_date} to {end_date}"
                empty_fig = create_empty_chart(empty_message)
                empty_chart_json = json.dumps(empty_fig, cls=plotly.utils.PlotlyJSONEncoder)
                return jsonify({
                    'success': True, 
                    'charts': {
                        'daily_overview': empty_chart_json,
                        'hourly_analysis': empty_chart_json,
                        'net_flow': empty_chart_json,
                        'energy_balance': empty_chart_json,
                        'consumption_pattern': empty_chart_json
                    }
                })
        
        # Check if date range is more than 30 days for rolling averages
        date_range_days = 0
        if start_date and end_date:
            date_range_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
        elif not filtered_df.empty:
            date_range_days = (filtered_df['date'].max() - filtered_df['date'].min()).days
        
        # Generate chart options
        show_temperature = 'show_temperature' in options
        use_rolling_avg = 'use_rolling_avg' in options and date_range_days > 30
        
        charts = {}
        
        # Generate all charts
        try:
            # Daily Overview Chart
            fig = create_daily_overview_chart(filtered_df, show_temperature, use_rolling_avg)
            charts['daily_overview'] = json.dumps(fix_chart_binary_data(fig.to_dict()), cls=plotly.utils.PlotlyJSONEncoder)
        except Exception as e:
            charts['daily_overview'] = json.dumps(create_empty_chart(f"Error generating daily overview: {str(e)}"), cls=plotly.utils.PlotlyJSONEncoder)
        
        try:
            # Hourly Analysis Chart (only if raw data available)
            if not raw_df.empty:
                fig = create_hourly_analysis_chart(raw_df, start_date, end_date)
                charts['hourly_analysis'] = json.dumps(fix_chart_binary_data(fig.to_dict()), cls=plotly.utils.PlotlyJSONEncoder)
            else:
                charts['hourly_analysis'] = json.dumps(create_empty_chart("Hourly raw data not available"), cls=plotly.utils.PlotlyJSONEncoder)
        except Exception as e:
            charts['hourly_analysis'] = json.dumps(create_empty_chart(f"Error generating hourly analysis: {str(e)}"), cls=plotly.utils.PlotlyJSONEncoder)
        
        try:
            # Net Flow Chart
            fig = create_net_flow_chart(filtered_df, show_temperature, use_rolling_avg)
            charts['net_flow'] = json.dumps(fix_chart_binary_data(fig.to_dict()), cls=plotly.utils.PlotlyJSONEncoder)
        except Exception as e:
            charts['net_flow'] = json.dumps(create_empty_chart(f"Error generating net flow: {str(e)}"), cls=plotly.utils.PlotlyJSONEncoder)
        
        try:
            # Energy Balance Chart
            fig = create_energy_balance_chart(filtered_df)
            charts['energy_balance'] = json.dumps(fix_chart_binary_data(fig.to_dict()), cls=plotly.utils.PlotlyJSONEncoder)
        except Exception as e:
            charts['energy_balance'] = json.dumps(create_empty_chart(f"Error generating energy balance: {str(e)}"), cls=plotly.utils.PlotlyJSONEncoder)
        
        try:
            # Consumption Pattern Chart
            fig = create_consumption_pattern_chart(filtered_df, use_rolling_avg)
            charts['consumption_pattern'] = json.dumps(fix_chart_binary_data(fig.to_dict()), cls=plotly.utils.PlotlyJSONEncoder)
        except Exception as e:
            charts['consumption_pattern'] = json.dumps(create_empty_chart(f"Error generating consumption pattern: {str(e)}"), cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({'success': True, 'charts': charts})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def fix_chart_binary_data(chart_dict):
    """Fix any binary encoded arrays in chart data to prevent frontend issues."""
    # Convert any binary encoded arrays to regular lists
    for trace in chart_dict.get('data', []):
        for key in ['x', 'y', 'z']:
            if key in trace and isinstance(trace[key], dict):
                if 'dtype' in trace[key] and 'bdata' in trace[key]:
                    # Convert binary data back to regular array
                    import numpy as np
                    import base64
                    binary_data = base64.b64decode(trace[key]['bdata'])
                    dtype = trace[key]['dtype']
                    array = np.frombuffer(binary_data, dtype=dtype)
                    trace[key] = array.tolist()  # Convert to regular Python list
    return chart_dict

@app.route('/api/cache-password', methods=['POST'])
def api_cache_password():
    """Cache encryption password for the session."""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({'success': False, 'error': 'Password required'}), 400
        
        # Try to cache the password
        success = credential_manager.cache_password(password)
        
        if success:
            return jsonify({'success': True, 'message': 'Password cached successfully'})
        else:
            return jsonify({'success': False, 'error': 'Invalid password or no encrypted credentials found'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/refresh-data', methods=['POST'])
def api_refresh_data():
    """API endpoint for refreshing both consumption and pricing data."""
    try:
        data = request.get_json()
        refresh_type = data.get('type', 'all')  # 'consumption', 'pricing', 'all', 'lifetime'
        days_back = data.get('days', 30)  # Number of days to fetch
        force_lifetime = data.get('lifetime', False)  # Force lifetime refresh
        delete_existing = data.get('delete_existing', False)  # Delete existing data first
        
        results = {
            'success': True,
            'consumption': {'status': 'skipped'},
            'pricing': {'status': 'skipped'},
            'errors': []
        }
        
        # Handle lifetime refresh
        if refresh_type == 'lifetime' or force_lifetime:
            try:
                if delete_existing:
                    delete_result = delete_consumption_data()
                    if delete_result['status'] != 'success':
                        results['errors'].append(f"Failed to delete existing data: {delete_result['message']}")
                
                consumption_result = refresh_consumption_data_lifetime()
                results['consumption'] = consumption_result
            except Exception as e:
                results['consumption'] = {'status': 'error', 'message': str(e)}
                results['errors'].append(f"Lifetime refresh failed: {str(e)}")
        
        # Refresh consumption data (regular)
        elif refresh_type in ['consumption', 'all']:
            try:
                consumption_result = refresh_consumption_data(days_back)
                results['consumption'] = consumption_result
            except Exception as e:
                results['consumption'] = {'status': 'error', 'message': str(e)}
                results['errors'].append(f"Consumption refresh failed: {str(e)}")
        
        # Refresh pricing data
        if refresh_type in ['pricing', 'all']:
            try:
                pricing_result = refresh_pricing_data()
                results['pricing'] = pricing_result
            except Exception as e:
                results['pricing'] = {'status': 'error', 'message': str(e)}
                results['errors'].append(f"Pricing refresh failed: {str(e)}")
        
        # If there were any errors but some succeeded, mark as partial success
        if results['errors'] and (results['consumption'].get('status') == 'success' or results['pricing'].get('status') == 'success'):
            results['success'] = 'partial'
        elif results['errors']:
            results['success'] = False
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def delete_consumption_data():
    """Safely delete existing consumption data from database."""
    try:
        # Get current stats before deletion
        stats_before = database_utils.get_data_stats()
        
        # Delete consumption data from database
        success = database_utils.delete_all_consumption_data()
        
        if success:
            return {
                'status': 'success',
                'message': f'Deleted consumption data from database',
                'deleted_records': {
                    'consumption_raw': stats_before.get('consumption_raw', 0),
                    'consumption_daily': stats_before.get('consumption_daily', 0),
                    'consumption_monthly': stats_before.get('consumption_monthly', 0)
                }
            }
        else:
            return {
                'status': 'error',
                'message': 'Failed to delete consumption data from database'
            }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error deleting consumption data: {str(e)}'
        }

def refresh_consumption_data_lifetime():
    """Refresh consumption data using lifetime fetcher (all available data)."""
    import subprocess
    import os
    
    # Check for API credentials using secure credential manager
    api_key, account_number, error_msg = get_api_credentials()
    
    if not api_key or not account_number:
        return {
            'status': 'error',
            'message': error_msg or 'API credentials not found. Please run credential_manager.py to set up secure credentials.'
        }
    
    # Set environment variables for the subprocess
    env = os.environ.copy()
    env['OCTOPUS_API_KEY'] = api_key
    env['OCTOPUS_ACCOUNT_NUMBER'] = account_number
    # Fix Unicode encoding issues on Windows
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        # Check if octopus_lifetime_fetcher.py exists
        if os.path.exists('octopus_lifetime_fetcher.py'):
            script_name = 'octopus_lifetime_fetcher.py'
        elif os.path.exists('octopus_energy_fetcher.py'):
            script_name = 'octopus_energy_fetcher.py'
        else:
            return {
                'status': 'error',
                'message': 'No consumption data fetcher script found. Please ensure octopus_lifetime_fetcher.py exists.'
            }
        
        # Run the fetcher script with --lifetime flag
        cmd = ['python', script_name, '--lifetime']
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800, encoding='utf-8', errors='replace')  # 30 minute timeout for lifetime
        
        if result.returncode == 0:
            # Check database statistics after refresh
            stats_after = database_utils.get_data_stats()
            files_created = []
            if stats_after.get("consumption_raw", 0) > 0:
                files_created.append("Database: consumption_raw")
            if stats_after.get("consumption_daily", 0) > 0:
                files_created.append("Database: consumption_daily")
            
            return {
                'status': 'success',
                'message': 'Successfully fetched lifetime consumption data',
                'files_created': files_created,
                'details': result.stdout
            }
        else:
            return {
                'status': 'error',
                'message': f'Lifetime fetcher script failed: {result.stderr}',
                'details': result.stdout
            }
            
    except subprocess.TimeoutExpired:
        return {
            'status': 'error',
            'message': 'Lifetime data fetch timed out after 30 minutes. This may happen with very large datasets.'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@app.route('/api/delete-consumption-data', methods=['POST'])
def api_delete_consumption_data():
    """API endpoint to delete existing consumption data files."""
    try:
        result = delete_consumption_data()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def refresh_consumption_data(days_back=30):
    """Refresh consumption data using the existing API fetcher."""
    import subprocess
    import os
    from datetime import datetime, timedelta
    
    # Check for API credentials using secure credential manager
    api_key, account_number, error_msg = get_api_credentials()
    
    if not api_key or not account_number:
        return {
            'status': 'error',
            'message': error_msg or 'API credentials not found. Please run credential_manager.py to set up secure credentials.'
        }
    
    # Set environment variables for the subprocess
    env = os.environ.copy()
    env['OCTOPUS_API_KEY'] = api_key
    env['OCTOPUS_ACCOUNT_NUMBER'] = account_number
    # Fix Unicode encoding issues on Windows
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        # Check if octopus_lifetime_fetcher.py exists
        if os.path.exists('octopus_lifetime_fetcher.py'):
            script_name = 'octopus_lifetime_fetcher.py'
        elif os.path.exists('octopus_energy_fetcher.py'):
            script_name = 'octopus_energy_fetcher.py'
        else:
            return {
                'status': 'error',
                'message': 'No consumption data fetcher script found. Please ensure octopus_lifetime_fetcher.py or octopus_energy_fetcher.py exists.'
            }
        
        # Run the fetcher script
        cmd = ['python', script_name, '--days', str(days_back)]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            # Check database statistics after refresh
            stats_after = database_utils.get_data_stats()
            files_created = []
            if stats_after.get("consumption_raw", 0) > 0:
                files_created.append("Database: consumption_raw")
            if stats_after.get("consumption_daily", 0) > 0:
                files_created.append("Database: consumption_daily")
            
            return {
                'status': 'success',
                'message': f'Successfully fetched {days_back} days of consumption data',
                'files_created': files_created,
                'details': result.stdout
            }
        else:
            return {
                'status': 'error',
                'message': f'Fetcher script failed: {result.stderr}',
                'details': result.stdout
            }
            
    except subprocess.TimeoutExpired:
        return {
            'status': 'error',
            'message': f'Data fetch timed out after 5 minutes. Try fetching fewer days.'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

def refresh_pricing_data():
    """Refresh pricing data using the existing tariff refresh functionality."""
    if not TARIFF_AVAILABLE:
        return {
            'status': 'error',
            'message': 'Tariff tracker not available'
        }
    
    try:
        # Use the existing tariff refresh functionality
        mgr = get_manager()
        if not mgr:
            return {
                'status': 'error',
                'message': 'Could not initialize tariff manager'
            }
        
        # Refresh all tariff periods
        refresh_results = []
        
        # Get all import periods and refresh them
        import_periods = mgr.get_import_periods()
        for period in import_periods:
            try:
                mgr.refresh_period_rates(period.id)
                refresh_results.append(f"Refreshed import period: {period.tariff_code}")
            except Exception as e:
                refresh_results.append(f"Failed to refresh import period {period.tariff_code}: {str(e)}")
        
        # Get all export periods and refresh them
        export_periods = mgr.get_export_periods()
        for period in export_periods:
            try:
                mgr.refresh_period_rates(period.id)
                refresh_results.append(f"Refreshed export period: {period.tariff_code}")
            except Exception as e:
                refresh_results.append(f"Failed to refresh export period {period.tariff_code}: {str(e)}")
        
        # Regenerate pricing data CSV if we have the script
        if os.path.exists('generate_pricing_data.py'):
            try:
                import subprocess
                result = subprocess.run(['python', 'generate_pricing_data.py'], 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    refresh_results.append("Regenerated pricing_raw.csv successfully")
                else:
                    refresh_results.append(f"Failed to regenerate pricing_raw.csv: {result.stderr}")
            except Exception as e:
                refresh_results.append(f"Failed to regenerate pricing data: {str(e)}")
        
        return {
            'status': 'success',
            'message': 'Pricing data refresh completed',
            'details': refresh_results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Pricing refresh failed: {str(e)}'
        }

if __name__ == '__main__':
    print("🐙 Starting Unified Octopus Energy Dashboard...")
    print("🔌 Solar Dashboard: Available" if not daily_df.empty else "🔌 Solar Dashboard: No data")
    print("⚡ Tariff Tracker: Available" if TARIFF_AVAILABLE else "⚡ Tariff Tracker: Not available")
    print("🌐 Dashboard will be available at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 