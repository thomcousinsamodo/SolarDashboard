import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
from pathlib import Path
import os

# Import weather integration
try:
    from weather_integration import correlate_weather_solar, create_weather_solar_chart, get_weather_correlation_stats
    WEATHER_AVAILABLE = True
except ImportError:
    print("⚠️  Weather integration not available")
    WEATHER_AVAILABLE = False

# Import price calculations
try:
    from price_config import PriceCalculator, format_currency, DEFAULT_TARIFFS, get_real_pricing_config
    PRICING_AVAILABLE = True
except ImportError:
    print("⚠️  Price calculations not available")
    PRICING_AVAILABLE = False

# Load data
def load_data():
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
                # Sort by date to ensure proper ordering
                df = df.sort_values('date').reset_index(drop=True)
            elif key == 'raw':
                df['interval_start'] = pd.to_datetime(df['interval_start'])
                df['interval_end'] = pd.to_datetime(df['interval_end'])
                # Sort by interval_start to ensure proper ordering
                df = df.sort_values('interval_start').reset_index(drop=True)
            dataframes[key] = df
        else:
            print(f"Warning: {filename} not found")
            dataframes[key] = pd.DataFrame()
    
    return dataframes

# Load the data
data = load_data()
daily_df = data['daily']
raw_df = data['raw']

# Debug: Print actual date range
if not daily_df.empty:
    print(f"📅 Loaded daily data: {len(daily_df)} records")
    print(f"📅 Date range: {daily_df['date'].min()} to {daily_df['date'].max()}")
    print(f"📅 Date types: {daily_df['date'].dtype}")
else:
    print("❌ No daily data loaded")

# Calculate summary statistics
def calculate_summary_stats(df):
    """Calculate summary statistics for the dashboard"""
    if df.empty:
        return {}
    
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    total_import = import_data['total_kwh'].sum() if not import_data.empty else 0
    total_export = export_data['total_kwh'].sum() if not export_data.empty else 0
    net_consumption = total_import - total_export
    
    # Calculate average daily values
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

stats = calculate_summary_stats(daily_df)

# Initialize price calculator with real API pricing
if PRICING_AVAILABLE:
    try:
        # Get real pricing configuration from API
        real_pricing_config = get_real_pricing_config()
        price_calculator = PriceCalculator(real_pricing_config)
        price_stats = price_calculator.get_summary_stats(daily_df) if not daily_df.empty else {}
        
        # Show pricing info in console
        data_source = real_pricing_config.get('data_source', 'default')
        if data_source == 'octopus_api':
            print("💰 Using real Octopus Energy API pricing:")
            print(f"   Import: {real_pricing_config['import_rate']}p/kWh")
            print(f"   Export: {real_pricing_config['export_rate']}p/kWh")
            print(f"   Standing: {real_pricing_config['standing_charge_daily']}p/day")
        else:
            print("📊 Using default UK energy tariffs")
            
    except Exception as e:
        print(f"⚠️  Error initializing real pricing: {e}")
        price_calculator = PriceCalculator()
        price_stats = price_calculator.get_summary_stats(daily_df) if not daily_df.empty else {}
else:
    price_calculator = None
    price_stats = {}

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
        
        # Ensure date formats match
        weather_df['date'] = pd.to_datetime(weather_df['date'])
        weather_df = weather_df.sort_values('date')
        
        # Add rolling averages if requested
        if use_rolling_avg:
            # Calculate rolling window based on data range (same logic as energy data)
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

def add_rolling_averages(df, column='total_kwh', window=7):
    """Add rolling averages to the dataframe"""
    df_copy = df.copy()
    df_copy = df_copy.sort_values('date')
    
    for meter_type in df_copy['meter_type'].unique():
        mask = df_copy['meter_type'] == meter_type
        if column in df_copy.columns:
            df_copy.loc[mask, 'rolling_avg'] = df_copy.loc[mask, column].rolling(window=window, center=True).mean()
        else:
            df_copy.loc[mask, 'rolling_avg'] = df_copy.loc[mask, 'total_kwh'].rolling(window=window, center=True).mean()
    
    return df_copy

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Solar Energy Dashboard - Octopus Tracker"

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

# Create dashboard layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("☀️ Solar Energy Dashboard", 
                   className="text-center mb-4",
                   style={'color': colors['primary'], 'fontWeight': 'bold'}),
            html.H5("Octopus Energy Consumption & Solar Export Analysis", 
                   className="text-center text-muted mb-4")
        ])
    ]),
    
    # Energy Summary Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="total-import-value", 
                           className="card-title text-danger"),
                    html.P("Total Grid Import", className="card-text text-muted"),
                    html.Small(id="avg-import-value", 
                             className="text-muted")
                ])
            ], color="danger", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="total-export-value", 
                           className="card-title text-success"),
                    html.P("Total Solar Export", className="card-text text-muted"),
                    html.Small(id="avg-export-value", 
                             className="text-muted")
                ])
            ], color="success", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="net-consumption-value", 
                           className="card-title text-primary"),
                    html.P("Net Consumption", className="card-text text-muted"),
                    html.Small("Import - Export", className="text-muted")
                ])
            ], color="primary", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="self-sufficiency-value", 
                           className="card-title text-warning"),
                    html.P("Self Sufficiency", className="card-text text-muted"),
                    html.Small("Export/Import ratio", className="text-muted")
                ])
            ], color="warning", outline=True)
        ], width=3),
    ], className="mb-4"),
    
    # Financial Summary Cards (if pricing available)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="total-bill-value", 
                           className="card-title text-danger"),
                    html.P("Total Energy Bill", className="card-text text-muted"),
                    html.Small(id="avg-bill-value", 
                             className="text-muted")
                ])
            ], color="danger", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="total-earnings-value", 
                           className="card-title text-success"),
                    html.P("Solar Export Earnings", className="card-text text-muted"),
                    html.Small(id="avg-earnings-value", 
                             className="text-muted")
                ])
            ], color="success", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="net-cost-value", 
                           className="card-title text-primary"),
                    html.P("Net Energy Cost", className="card-text text-muted"),
                    html.Small("Bills - Earnings", className="text-muted")
                ])
            ], color="primary", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="savings-rate-value", 
                           className="card-title text-warning"),
                    html.P("Solar Savings Rate", className="card-text text-muted"),
                    html.Small("Earnings vs Bills", className="text-muted")
                ])
            ], color="warning", outline=True)
        ], width=3),
    ], className="mb-4") if PRICING_AVAILABLE else html.Div(),
    
    # Pricing Information Card (if pricing available)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("💰 Pricing Information", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="pricing-info-content")
                ])
            ], color="info", outline=True)
        ], width=12)
    ], className="mb-4") if PRICING_AVAILABLE else html.Div(),
    
    # Chart Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Chart Controls", className="card-title"),
                    
                    # Quick Date Range Buttons
                    dbc.Row([
                        dbc.Col([
                            html.Label("Quick Select:", className="mb-2"),
                            dbc.ButtonGroup([
                                dbc.Button("Lifetime", id="btn-lifetime", color="primary", outline=True, size="sm"),
                                dbc.Button("Since Export", id="btn-export-start", color="success", outline=True, size="sm"),
                                dbc.Button("Since Move-in", id="btn-move-in", color="info", outline=True, size="sm"),
                                dbc.Button("Last 30 Days", id="btn-last-30", color="secondary", outline=True, size="sm")
                            ], className="mb-2 d-flex flex-wrap")
                        ], width=12)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Label("Chart Type:"),
                            dcc.Dropdown(
                                id='chart-type-dropdown',
                                options=[
                                    {'label': 'Daily Overview', 'value': 'daily'},
                                    {'label': 'Hourly Analysis', 'value': 'hourly'},
                                    {'label': 'Net Energy Flow', 'value': 'net_flow'}
                                ],
                                value='daily',
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Chart Options:"),
                            dbc.Checklist(
                                id='chart-options-checklist',
                                options=[
                                    {'label': ' Show Temperature', 'value': 'temperature'},
                                    {'label': ' Rolling Averages (>30 days)', 'value': 'rolling_avg'},
                                    {'label': ' Price View (£)', 'value': 'price_view', 'disabled': not PRICING_AVAILABLE}
                                ],
                                value=['rolling_avg'],  # Default to rolling averages enabled
                                switch=True,
                                inline=True
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Custom Date Range:"),
                            dcc.DatePickerRange(
                                id='date-picker-range',
                                start_date=daily_df['date'].min() if not daily_df.empty else None,
                                end_date=daily_df['date'].max() if not daily_df.empty else None,
                                min_date_allowed=daily_df['date'].min() if not daily_df.empty else None,
                                max_date_allowed=daily_df['date'].max() if not daily_df.empty else None,
                                display_format='YYYY-MM-DD',
                                initial_visible_month=daily_df['date'].min() if not daily_df.empty else None
                            ),
                            html.Small(
                                f"📅 Data available: {daily_df['date'].min().strftime('%Y-%m-%d') if not daily_df.empty else 'No data'} to {daily_df['date'].max().strftime('%Y-%m-%d') if not daily_df.empty else 'No data'}",
                                className="text-muted mt-1 d-block"
                            )
                        ], width=4)
                    ])
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Main Charts
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='main-chart')
        ], width=12)
    ], className="mb-4"),
    
    # Secondary Charts Row
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='energy-balance-chart')
        ], width=6),
        dbc.Col([
            dcc.Graph(id='consumption-pattern-chart')
        ], width=6)
    ], className="mb-4"),
    
    # Weather Correlation Row (if available)
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='weather-correlation-chart')
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🌤️ Weather Correlations", className="card-title"),
                    html.P("📍 Chesterfield, Derbyshire (S40 2EG)", className="text-muted small mb-2"),
                    html.Div(id="weather-correlation-stats")
                ])
            ])
        ], width=4)
    ], className="mb-4") if WEATHER_AVAILABLE else html.Div(),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                  f"Data points: {len(daily_df)} days", 
                  className="text-center text-muted")
        ])
    ])
    
], fluid=True, style={'backgroundColor': colors['background']})

# Callbacks for date range buttons
@app.callback(
    Output('date-picker-range', 'start_date'),
    Output('date-picker-range', 'end_date'),
    [Input('btn-lifetime', 'n_clicks'),
     Input('btn-export-start', 'n_clicks'),
     Input('btn-move-in', 'n_clicks'),
     Input('btn-last-30', 'n_clicks')],
    prevent_initial_call=True
)
def update_date_range(lifetime_clicks, export_clicks, movein_clicks, last30_clicks):
    """Update date range based on preset buttons"""
    ctx = callback_context
    if not ctx.triggered:
        return daily_df['date'].min(), daily_df['date'].max()
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-lifetime':
        # Full data range
        return daily_df['date'].min(), daily_df['date'].max()
    elif button_id == 'btn-export-start':
        # Since export began (find first non-zero export)
        export_data = daily_df[daily_df['meter_type'] == 'export']
        if not export_data.empty:
            first_export = export_data[export_data['total_kwh'] > 0]['date'].min()
            return first_export, daily_df['date'].max()
        return daily_df['date'].min(), daily_df['date'].max()
    elif button_id == 'btn-move-in':
        # Since move-in date (May 16, 2025)
        move_in_date = pd.to_datetime('2025-05-16')
        return move_in_date, daily_df['date'].max()
    elif button_id == 'btn-last-30':
        # Last 30 days
        end_date = daily_df['date'].max()
        start_date = end_date - pd.Timedelta(days=30)
        return start_date, end_date
    
    return daily_df['date'].min(), daily_df['date'].max()


# Main callback for charts and metrics
outputs = [
    Output('main-chart', 'figure'),
    Output('energy-balance-chart', 'figure'),
    Output('consumption-pattern-chart', 'figure'),
    Output('total-import-value', 'children'),
    Output('total-export-value', 'children'),
    Output('net-consumption-value', 'children'),
    Output('self-sufficiency-value', 'children'),
    Output('avg-import-value', 'children'),
    Output('avg-export-value', 'children')
]

# Add financial outputs if available
if PRICING_AVAILABLE:
    outputs.extend([
        Output('total-bill-value', 'children'),
        Output('total-earnings-value', 'children'),
        Output('net-cost-value', 'children'),
        Output('savings-rate-value', 'children'),
        Output('avg-bill-value', 'children'),
        Output('avg-earnings-value', 'children'),
        Output('pricing-info-content', 'children')
    ])

# Add weather outputs if available
if WEATHER_AVAILABLE:
    outputs.extend([
        Output('weather-correlation-chart', 'figure'),
        Output('weather-correlation-stats', 'children')
    ])

@app.callback(
    outputs,
    [Input('chart-type-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('chart-options-checklist', 'value')]
)
def update_charts(chart_type, start_date, end_date, chart_options):
    # Ensure chart_options is a list
    if chart_options is None:
        chart_options = []
    
    # Filter data by date range
    filtered_df = daily_df.copy()
    if start_date and end_date and not daily_df.empty:
        filtered_df = daily_df[
            (daily_df['date'] >= start_date) & 
            (daily_df['date'] <= end_date)
        ]
        
        # Check if filtered data is empty due to date range selection
        if filtered_df.empty:
            empty_message = f"No data available for selected date range<br>{start_date} to {end_date}"
            empty_fig = create_empty_chart(empty_message)
            return empty_fig, empty_fig, empty_fig, "0.0 kWh", "0.0 kWh", "0.0 kWh", "0.0%", "No data", "No data"
    
    # Calculate dynamic statistics for the filtered period
    filtered_stats = calculate_summary_stats(filtered_df)
    
    # Format metric values
    total_import = f"{filtered_stats.get('total_import', 0):.1f} kWh"
    total_export = f"{filtered_stats.get('total_export', 0):.1f} kWh"
    net_consumption = f"{filtered_stats.get('net_consumption', 0):.1f} kWh"
    self_sufficiency = f"{filtered_stats.get('self_sufficiency', 0):.1f}%"
    avg_import = f"Avg: {filtered_stats.get('avg_daily_import', 0):.1f} kWh/day"
    avg_export = f"Avg: {filtered_stats.get('avg_daily_export', 0):.1f} kWh/day"
    
    # Check if date range is more than 30 days for rolling averages
    date_range_days = 0
    if start_date and end_date:
        date_range_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    elif not filtered_df.empty:
        date_range_days = (filtered_df['date'].max() - filtered_df['date'].min()).days
    
    use_rolling_avg = 'rolling_avg' in chart_options and date_range_days > 30
    show_temperature = 'temperature' in chart_options
    show_price_view = 'price_view' in chart_options and PRICING_AVAILABLE
    
    # Calculate financial metrics if pricing is available
    if PRICING_AVAILABLE and price_calculator:
        filtered_price_stats = price_calculator.get_summary_stats(filtered_df)
    else:
        filtered_price_stats = {}
    
    # Main Chart
    if chart_type == 'daily':
        main_fig = create_daily_overview_chart(filtered_df, show_temperature, use_rolling_avg, show_price_view)
    elif chart_type == 'hourly' and not raw_df.empty:
        main_fig = create_hourly_analysis_chart(raw_df, start_date, end_date)
    elif chart_type == 'net_flow':
        main_fig = create_net_flow_chart(filtered_df, show_temperature, use_rolling_avg, show_price_view)
    else:
        main_fig = create_empty_chart("No data available")
    
    # Energy Balance Chart
    balance_fig = create_energy_balance_chart(filtered_df)
    
    # Consumption Pattern Chart
    pattern_fig = create_consumption_pattern_chart(filtered_df, use_rolling_avg)
    
    # Weather correlation (if available)
    weather_fig = None
    weather_stats = None
    
    if WEATHER_AVAILABLE:
        try:
            # Create weather correlation
            weather_df = correlate_weather_solar(filtered_df)
            weather_fig = create_weather_solar_chart(weather_df, use_rolling_avg)
            
            # Get correlation stats
            correlations = get_weather_correlation_stats(weather_df)
            if correlations:
                weather_stats = html.Div([
                    html.P([
                        html.Strong("🌡️ Temperature: "),
                        f"{correlations.get('temperature_correlation', 0):.3f}"
                    ], className="mb-1"),
                    html.P([
                        html.Strong("☀️ Sunshine: "),
                        f"{correlations.get('sunshine_correlation', 0):.3f}"
                    ], className="mb-1"),
                    html.P([
                        html.Strong("☁️ Cloud Cover: "),
                        f"{correlations.get('cloud_correlation', 0):.3f}"
                    ], className="mb-1"),
                    html.Small("Correlation values: -1 to +1", className="text-muted")
                ])
            else:
                weather_stats = html.P("No correlation data available", className="text-muted")
                
        except Exception as e:
            print(f"Weather correlation error: {e}")
            weather_fig = create_empty_chart("Weather data unavailable")
            weather_stats = html.P("Weather data unavailable", className="text-muted")
    
    # Format financial metrics
    if PRICING_AVAILABLE and filtered_price_stats:
        total_bill = format_currency(filtered_price_stats.get('total_bill', 0))
        total_earnings = format_currency(filtered_price_stats.get('total_export_earnings', 0))
        net_cost = format_currency(filtered_price_stats.get('net_cost', 0))
        avg_bill = f"Avg: {format_currency(filtered_price_stats.get('avg_daily_bill', 0))}/day"
        avg_earnings = f"Avg: {format_currency(filtered_price_stats.get('avg_daily_savings', 0))}/day"
        
        # Calculate savings rate percentage
        total_bill_amount = filtered_price_stats.get('total_bill', 0)
        total_earnings_amount = filtered_price_stats.get('total_export_earnings', 0)
        savings_rate = (total_earnings_amount / total_bill_amount * 100) if total_bill_amount > 0 else 0
        savings_rate_text = f"{savings_rate:.1f}%"
        
        # Create pricing info content
        pricing_config = price_calculator.config if price_calculator else {}
        data_source = pricing_config.get('data_source', 'default')
        
        if data_source == 'octopus_api':
            pricing_info = html.Div([
                html.P([
                    html.Strong("🌐 Real Octopus Energy API Data"), 
                    html.Br(),
                    html.Small(f"Last updated: {pricing_config.get('last_updated', 'Unknown')[:16].replace('T', ' ')}", className="text-muted")
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col([
                        html.P([html.Strong("Import Rate: "), f"{pricing_config.get('import_rate', 0)}p/kWh"], className="mb-1"),
                        html.P([html.Strong("Export Rate: "), f"{pricing_config.get('export_rate', 0)}p/kWh"], className="mb-1"),
                    ], width=6),
                    dbc.Col([
                        html.P([html.Strong("Standing Charge: "), f"{pricing_config.get('standing_charge_daily', 0)}p/day"], className="mb-1"),
                        html.P([html.Strong("Currency: "), pricing_config.get('currency', 'GBP')], className="mb-1"),
                    ], width=6)
                ]),
                html.Hr(),
                html.P([
                    html.I(className="fas fa-info-circle"),
                    " These are your actual Octopus Energy tariff rates. Costs shown match your real bills."
                ], className="text-info mb-0")
            ])
        else:
            pricing_info = html.Div([
                html.P([
                    html.Strong("📊 Default UK Energy Tariffs"),
                    html.Br(),
                    html.Small("Generic pricing - connect API for real rates", className="text-muted")
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col([
                        html.P([html.Strong("Import Rate: "), f"{pricing_config.get('import_rate', 0)}p/kWh"], className="mb-1"),
                        html.P([html.Strong("Export Rate: "), f"{pricing_config.get('export_rate', 0)}p/kWh"], className="mb-1"),
                    ], width=6),
                    dbc.Col([
                        html.P([html.Strong("Standing Charge: "), f"{pricing_config.get('standing_charge_daily', 0)}p/day"], className="mb-1"),
                        html.P([html.Strong("Currency: "), pricing_config.get('currency', 'GBP')], className="mb-1"),
                    ], width=6)
                ]),
                html.Hr(),
                html.P([
                    html.I(className="fas fa-exclamation-triangle"),
                    " Set OCTOPUS_API_KEY and OCTOPUS_ACCOUNT_NUMBER environment variables for real pricing."
                ], className="text-warning mb-0")
            ])
    else:
        total_bill = "£0.00"
        total_earnings = "£0.00"
        net_cost = "£0.00"
        avg_bill = "No data"
        avg_earnings = "No data"
        savings_rate_text = "0.0%"
        pricing_info = html.P("Pricing information not available", className="text-muted")
    
    # Return based on what's available
    base_returns = [main_fig, balance_fig, pattern_fig, total_import, total_export, net_consumption, self_sufficiency, avg_import, avg_export]
    
    # Add financial returns if available
    if PRICING_AVAILABLE:
        base_returns.extend([total_bill, total_earnings, net_cost, savings_rate_text, avg_bill, avg_earnings, pricing_info])
    
    if WEATHER_AVAILABLE:
        return base_returns + [weather_fig, weather_stats]
    else:
        return base_returns

def create_daily_overview_chart(df, show_temperature=False, use_rolling_avg=False, show_price_view=False):
    """Create daily overview chart showing import vs export"""
    if df.empty:
        return create_empty_chart("No daily data available")
    
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    # Calculate price data if price view is requested
    if show_price_view and PRICING_AVAILABLE and price_calculator:
        df_with_prices = price_calculator.calculate_daily_costs(df)
        import_data_prices = df_with_prices[df_with_prices['meter_type'] == 'import']
        export_data_prices = df_with_prices[df_with_prices['meter_type'] == 'export']
    else:
        df_with_prices = df
        import_data_prices = import_data
        export_data_prices = export_data
    
    # Create figure with secondary y-axis if temperature is requested
    if show_temperature:
        from plotly.subplots import make_subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
    
    # Apply rolling averages if requested
    if use_rolling_avg:
        if show_price_view:
            df_with_rolling = add_rolling_averages(df_with_prices, 'total_cost_pounds')
        else:
            df_with_rolling = add_rolling_averages(df)
        import_data_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'import']
        export_data_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'export']
        
        # Add rolling average traces (primary y-axis)
        if not import_data_rolling.empty:
            if show_price_view:
                y_values = import_data_rolling['rolling_avg']
                hover_template = '<b>Import (7-day avg)</b><br>Date: %{x}<br>Cost: £%{y:.2f}<extra></extra>'
                trace_name = 'Import Cost (7-day avg)'
            else:
                y_values = import_data_rolling['rolling_avg'] 
                hover_template = '<b>Import (7-day avg)</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
                trace_name = 'Import (7-day avg)'
                
            fig.add_trace(go.Scatter(
                x=import_data_rolling['date'],
                y=y_values,
                mode='lines',
                name=trace_name,
                line=dict(color=colors['import'], width=3),
                hovertemplate=hover_template
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
        # Add regular traces (primary y-axis)
        if not import_data.empty:
            if show_price_view:
                y_values = import_data_prices['total_cost_pounds']
                hover_template = '<b>Grid Import Cost</b><br>Date: %{x}<br>Cost: £%{y:.2f}<br>Energy: %{customdata:.2f} kWh<extra></extra>'
                trace_name = 'Grid Import Cost'
                customdata = import_data['total_kwh']
            else:
                y_values = import_data['total_kwh']
                hover_template = '<b>Grid Import</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
                trace_name = 'Grid Import'
                customdata = None
                
            fig.add_trace(go.Scatter(
                x=import_data['date'],
                y=y_values,
                customdata=customdata,
                mode='lines+markers',
                name=trace_name,
                line=dict(color=colors['import'], width=3),
                marker=dict(size=6),
                hovertemplate=hover_template
            ), secondary_y=False if show_temperature else None)
        
        if not export_data.empty:
            if show_price_view:
                y_values = export_data_prices['cost_pounds']
                hover_template = '<b>Solar Export Earnings</b><br>Date: %{x}<br>Earnings: £%{y:.2f}<br>Energy: %{customdata:.2f} kWh<extra></extra>'
                trace_name = 'Solar Export Earnings'
                customdata = export_data['total_kwh']
            else:
                y_values = export_data['total_kwh']
                hover_template = '<b>Solar Export</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<extra></extra>'
                trace_name = 'Solar Export'
                customdata = None
                
            fig.add_trace(go.Scatter(
                x=export_data['date'],
                y=y_values,
                customdata=customdata,
                mode='lines+markers',
                name=trace_name,
                line=dict(color=colors['export'], width=3),
                marker=dict(size=6),
                hovertemplate=hover_template
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
            if show_price_view:
                fig.update_yaxes(title_text='Cost (£)', secondary_y=False)
            else:
                fig.update_yaxes(title_text='Energy (kWh)', secondary_y=False)
            fig.update_yaxes(title_text='Temperature (°C)', secondary_y=True)
    
    # Update layout
    if show_price_view:
        title = 'Daily Energy Costs vs Earnings'
    else:
        title = 'Daily Energy Import vs Export'
        
    if use_rolling_avg:
        title += ' (with 7-day Rolling Average)'
    if show_temperature:
        title += ' & Temperature'
    
    y_axis_title = 'Cost (£)' if show_price_view else 'Energy (kWh)'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title=y_axis_title if not show_temperature else None,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_hourly_analysis_chart(df, start_date, end_date):
    """Create hourly analysis chart"""
    if df.empty:
        return create_empty_chart("No hourly data available")
    
    # Filter by date range if provided
    filtered_df = df.copy()
    if start_date and end_date:
        filtered_df = df[
            (df['interval_start'].dt.date >= pd.to_datetime(start_date).date()) &
            (df['interval_start'].dt.date <= pd.to_datetime(end_date).date())
        ]
    
    # Extract hour and calculate average consumption by hour
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

def create_net_flow_chart(df, show_temperature=False, use_rolling_avg=False, show_price_view=False):
    """Create net energy flow chart"""
    if df.empty:
        return create_empty_chart("No data available for net flow")
    
    # Calculate price data if price view is requested
    if show_price_view and PRICING_AVAILABLE and price_calculator:
        df_with_prices = price_calculator.calculate_daily_costs(df)
        value_column = 'total_cost_pounds'
        
        # For net flow in price view: import costs - export earnings
        pivot_df = df_with_prices.pivot_table(
            index='date', 
            columns='meter_type', 
            values=value_column, 
            fill_value=0
        ).reset_index()
        
        if 'import' not in pivot_df.columns:
            pivot_df['import'] = 0
        if 'export' not in pivot_df.columns:
            pivot_df['export'] = 0
            
        pivot_df['net_flow'] = pivot_df['import'] - pivot_df['export']  # Net cost (positive = money spent)
    else:
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
    if show_price_view:
        hover_template = '<b>Net Cost</b><br>Date: %{x}<br>Net: £%{y:.2f}<br>' + \
                        '<i>Positive = Money Spent, Negative = Money Saved</i><extra></extra>'
        trace_name = 'Net Energy Cost'
    else:
        hover_template = '<b>Net Flow</b><br>Date: %{x}<br>Net: %{y:.2f} kWh<br>' + \
                        '<i>Positive = Grid Import, Negative = Solar Export</i><extra></extra>'
        trace_name = 'Net Energy Flow'
        
    fig.add_trace(go.Bar(
        x=pivot_df['date'],
        y=pivot_df['net_flow'],
        marker_color=colors_net,
        name=trace_name,
        hovertemplate=hover_template
    ), secondary_y=False if show_temperature else None)
    
    # Add rolling average if requested
    if use_rolling_avg:
        pivot_df_sorted = pivot_df.sort_values('date')
        pivot_df_sorted['rolling_avg'] = pivot_df_sorted['net_flow'].rolling(window=7, center=True).mean()
        
        if show_price_view:
            rolling_hover = '<b>Net Cost (7-day avg)</b><br>Date: %{x}<br>Net: £%{y:.2f}<extra></extra>'
            rolling_name = 'Net Cost (7-day avg)'
        else:
            rolling_hover = '<b>Net Flow (7-day avg)</b><br>Date: %{x}<br>Net: %{y:.2f} kWh<extra></extra>'
            rolling_name = 'Net Flow (7-day avg)'
        
        fig.add_trace(go.Scatter(
            x=pivot_df_sorted['date'],
            y=pivot_df_sorted['rolling_avg'],
            mode='lines',
            name=rolling_name,
            line=dict(color='purple', width=3),
            hovertemplate=rolling_hover
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
            if show_price_view:
                fig.update_yaxes(title_text='Net Cost (£)', secondary_y=False)
            else:
                fig.update_yaxes(title_text='Net Energy (kWh)', secondary_y=False)
            fig.update_yaxes(title_text='Temperature (°C)', secondary_y=True)
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    
    # Update layout
    if show_price_view:
        title = 'Net Energy Cost (Import Cost - Export Earnings)'
        annotation_text = '🔴 Above zero: Net cost<br>🟢 Below zero: Net savings'
    else:
        title = 'Net Energy Flow (Import - Export)'
        annotation_text = '🔴 Above zero: Net consumption<br>🟢 Below zero: Net generation'
        
    if use_rolling_avg:
        title += ' (with 7-day Rolling Average)'
    if show_temperature:
        title += ' & Temperature'
    
    y_axis_title = 'Net Cost (£)' if show_price_view else 'Net Energy (kWh)'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title=y_axis_title if not show_temperature else None,
        template='plotly_white',
        annotations=[
            dict(
                x=0.02, y=0.98,
                xref='paper', yref='paper',
                text=annotation_text,
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
        # Standard 7-day rolling average for smaller datasets
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
    
    # Add data availability info if daily_df is available
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

# Run the app
if __name__ == '__main__':
    print("🚀 Starting Solar Energy Dashboard...")
    print("📊 Loading data...")
    print(f"   - Daily data: {len(daily_df)} records")
    print(f"   - Raw data: {len(raw_df)} records")
    print("🌐 Dashboard will be available at: http://127.0.0.1:8050")
    
    app.run(debug=True, host='127.0.0.1', port=8050)
