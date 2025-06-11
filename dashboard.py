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
    """Load consumption data from CSV files"""
    data_files = {
        'daily': 'octopus_consumption_daily.csv',
        'raw': 'octopus_consumption_raw.csv'
    }
    
    dataframes = {}
    for key, filename in data_files.items():
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            if key == 'daily':
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
            elif key == 'raw':
                df['interval_start'] = pd.to_datetime(df['interval_start'])
                df['interval_end'] = pd.to_datetime(df['interval_end'])
                df = df.sort_values('interval_start').reset_index(drop=True)
            dataframes[key] = df
        else:
            print(f"Warning: {filename} not found")
            dataframes[key] = pd.DataFrame()
    
    return dataframes

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
    # Get solar stats
    solar_stats = calculate_summary_stats(daily_df)
    
    # Get tariff summary if available
    tariff_summary = {}
    if TARIFF_AVAILABLE:
        try:
            mgr = get_manager()
            if mgr:
                tariff_summary = mgr.get_timeline_summary()
        except Exception as e:
            print(f"Error getting tariff summary: {e}")
            tariff_summary = {}
    
    return render_template('index.html', 
                         solar_stats=solar_stats, 
                         tariff_summary=tariff_summary,
                         tariff_available=TARIFF_AVAILABLE,
                         solar_data_available=not daily_df.empty)

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

if __name__ == '__main__':
    print("🐙 Starting Unified Octopus Energy Dashboard...")
    print("🔌 Solar Dashboard: Available" if not daily_df.empty else "🔌 Solar Dashboard: No data")
    print("⚡ Tariff Tracker: Available" if TARIFF_AVAILABLE else "⚡ Tariff Tracker: Not available")
    print("🌐 Dashboard will be available at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 