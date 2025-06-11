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

# Load enriched data (single source of truth)
def load_enriched_data():
    """Load enriched consumption data with pre-calculated costs"""
    data_files = {
        'daily_enriched': 'octopus_consumption_daily_enriched.csv',
        'enriched': 'octopus_consumption_enriched.csv'
    }
    
    dataframes = {}
    for key, filename in data_files.items():
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            if key == 'daily_enriched':
                df['date'] = pd.to_datetime(df['date'])
                # Sort by date to ensure proper ordering
                df = df.sort_values('date').reset_index(drop=True)
            elif key == 'enriched':
                df['interval_start'] = pd.to_datetime(df['interval_start'])
                # Sort by interval_start to ensure proper ordering
                df = df.sort_values('interval_start').reset_index(drop=True)
            dataframes[key] = df
        else:
            print(f"Warning: {filename} not found")
            dataframes[key] = pd.DataFrame()
    
    return dataframes

# Load the enriched data
enriched_data = load_enriched_data()
daily_enriched_df = enriched_data['daily_enriched']
enriched_df = enriched_data['enriched']

# Debug: Print actual date range
if not daily_enriched_df.empty:
    print(f"📅 Loaded enriched daily data: {len(daily_enriched_df)} records")
    print(f"📅 Date range: {daily_enriched_df['date'].min()} to {daily_enriched_df['date'].max()}")
    print(f"📅 Cost columns: {[col for col in daily_enriched_df.columns if 'cost' in col or 'rate' in col]}")
else:
    print("❌ No enriched daily data loaded")

# Calculate summary statistics from enriched data
def calculate_enriched_summary_stats(df):
    """Calculate summary statistics from enriched daily data"""
    if df.empty:
        return {}
    
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    # Energy statistics
    total_import = import_data['total_kwh'].sum() if not import_data.empty else 0
    total_export = export_data['total_kwh'].sum() if not export_data.empty else 0
    net_consumption = total_import - total_export
    
    # Cost statistics (pre-calculated in enriched data)
    total_import_cost = import_data['cost_pounds'].sum() if not import_data.empty else 0
    total_standing_charges = import_data['standing_charge_pounds'].sum() if not import_data.empty else 0
    total_export_earnings = export_data['cost_pounds'].sum() if not export_data.empty else 0
    
    total_bill = total_import_cost + total_standing_charges
    net_cost = total_bill - total_export_earnings
    
    # Calculate average daily values
    avg_daily_import = import_data['total_kwh'].mean() if not import_data.empty else 0
    avg_daily_export = export_data['total_kwh'].mean() if not export_data.empty else 0
    
    # Calculate per day financial averages
    days_count = len(df['date'].unique()) if not df.empty else 1
    
    return {
        'total_import': total_import,
        'total_export': total_export,
        'net_consumption': net_consumption,
        'avg_daily_import': avg_daily_import,
        'avg_daily_export': avg_daily_export,
        'self_sufficiency': (total_export / total_import * 100) if total_import > 0 else 0,
        'total_import_cost': total_import_cost,
        'total_export_earnings': total_export_earnings,
        'total_standing_charges': total_standing_charges,
        'total_bill': total_bill,
        'net_cost': net_cost,
        'avg_daily_bill': total_bill / days_count,
        'avg_daily_savings': total_export_earnings / days_count,
        'solar_savings_rate': (total_export_earnings / total_bill * 100) if total_bill > 0 else 0,
        'days_count': days_count
    }

enriched_stats = calculate_enriched_summary_stats(daily_enriched_df)

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Simplified Solar Dashboard - Bill-Accurate Pricing"

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
            html.H1("🧾 Simplified Solar Dashboard", 
                   className="text-center mb-4",
                   style={'color': colors['primary'], 'fontWeight': 'bold'}),
            html.H5("Bill-Accurate Pricing & Solar Analysis", 
                   className="text-center text-muted mb-4")
        ])
    ]),
    
    # Energy Summary Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{enriched_stats.get('total_import', 0):.1f} kWh", 
                           className="card-title text-danger"),
                    html.P("Total Grid Import", className="card-text text-muted"),
                    html.Small(f"Avg: {enriched_stats.get('avg_daily_import', 0):.1f} kWh/day", 
                             className="text-muted")
                ])
            ], color="danger", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{enriched_stats.get('total_export', 0):.1f} kWh", 
                           className="card-title text-success"),
                    html.P("Total Solar Export", className="card-text text-muted"),
                    html.Small(f"Avg: {enriched_stats.get('avg_daily_export', 0):.1f} kWh/day", 
                             className="text-muted")
                ])
            ], color="success", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{enriched_stats.get('net_consumption', 0):.1f} kWh", 
                           className="card-title text-primary"),
                    html.P("Net Consumption", className="card-text text-muted"),
                    html.Small("Import - Export", className="text-muted")
                ])
            ], color="primary", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{enriched_stats.get('self_sufficiency', 0):.1f}%", 
                           className="card-title text-warning"),
                    html.P("Self Sufficiency", className="card-text text-muted"),
                    html.Small("Export/Import ratio", className="text-muted")
                ])
            ], color="warning", outline=True)
        ], width=3),
    ], className="mb-4"),
    
    # Financial Summary Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"£{enriched_stats.get('total_bill', 0):.2f}", 
                           className="card-title text-danger"),
                    html.P("Total Energy Bill", className="card-text text-muted"),
                    html.Small(f"Avg: £{enriched_stats.get('avg_daily_bill', 0):.2f}/day", 
                             className="text-muted")
                ])
            ], color="danger", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"£{enriched_stats.get('total_export_earnings', 0):.2f}", 
                           className="card-title text-success"),
                    html.P("Solar Export Earnings", className="card-text text-muted"),
                    html.Small(f"Avg: £{enriched_stats.get('avg_daily_savings', 0):.2f}/day", 
                             className="text-muted")
                ])
            ], color="success", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"£{enriched_stats.get('net_cost', 0):.2f}", 
                           className="card-title text-primary"),
                    html.P("Net Energy Cost", className="card-text text-muted"),
                    html.Small("Bills - Earnings", className="text-muted")
                ])
            ], color="primary", outline=True)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{enriched_stats.get('solar_savings_rate', 0):.1f}%", 
                           className="card-title text-warning"),
                    html.P("Solar Savings Rate", className="card-text text-muted"),
                    html.Small("Earnings vs Bills", className="text-muted")
                ])
            ], color="warning", outline=True)
        ], width=3),
    ], className="mb-4"),
    
    # Pricing Information Card
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("🧾 Bill-Accurate Pricing System", className="mb-0")),
                dbc.CardBody([
                    html.P([
                        html.Strong("✅ Enriched Dataset Active"), 
                        html.Br(),
                        html.Small(f"Pre-calculated costs from {enriched_stats.get('days_count', 0)} days of data", className="text-muted")
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            html.P([html.Strong("Import Costs: "), f"£{enriched_stats.get('total_import_cost', 0):.2f}"], className="mb-1"),
                            html.P([html.Strong("Standing Charges: "), f"£{enriched_stats.get('total_standing_charges', 0):.2f}"], className="mb-1"),
                        ], width=6),
                        dbc.Col([
                            html.P([html.Strong("Export Earnings: "), f"£{enriched_stats.get('total_export_earnings', 0):.2f}"], className="mb-1"),
                            html.P([html.Strong("Data Source: "), "Bill-accurate tariff data"], className="mb-1"),
                        ], width=6)
                    ]),
                    html.Hr(),
                    html.P([
                        html.I(className="fas fa-check-circle"),
                        " Using precise half-hourly rates from your energy bills. Costs calculated with exact day/night tariffs."
                    ], className="text-success mb-0")
                ])
            ], color="success", outline=True)
        ], width=12)
    ], className="mb-4"),
    
    # Chart Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Chart Controls", className="card-title"),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Label("Chart Type:"),
                            dcc.Dropdown(
                                id='chart-type-dropdown',
                                options=[
                                    {'label': 'Daily Energy Overview', 'value': 'daily_energy'},
                                    {'label': 'Daily Cost Overview', 'value': 'daily_cost'},
                                    {'label': 'Rate Analysis', 'value': 'rate_analysis'},
                                    {'label': 'Net Energy Flow', 'value': 'net_flow'}
                                ],
                                value='daily_energy',
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Date Range:"),
                            dcc.DatePickerRange(
                                id='date-picker-range',
                                start_date=daily_enriched_df['date'].min() if not daily_enriched_df.empty else None,
                                end_date=daily_enriched_df['date'].max() if not daily_enriched_df.empty else None,
                                display_format='YYYY-MM-DD'
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Options:"),
                            dbc.Checklist(
                                id='chart-options',
                                options=[
                                    {'label': ' Show Tariff Transitions', 'value': 'transitions'},
                                    {'label': ' Rolling Averages', 'value': 'rolling'}
                                ],
                                value=['transitions'],
                                switch=True
                            )
                        ], width=4)
                    ])
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Main Chart
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
            dcc.Graph(id='cost-breakdown-chart')
        ], width=6)
    ], className="mb-4"),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P(f"📊 Enriched dataset: {len(daily_enriched_df)} days | "
                  f"💰 Bill-accurate pricing | "
                  f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                  className="text-center text-muted")
        ])
    ])
    
], fluid=True, style={'backgroundColor': colors['background']})

# Simplified callback for main chart
@app.callback(
    [Output('main-chart', 'figure'),
     Output('energy-balance-chart', 'figure'),
     Output('cost-breakdown-chart', 'figure')],
    [Input('chart-type-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('chart-options', 'value')]
)
def update_charts(chart_type, start_date, end_date, options):
    # Filter data by date range
    filtered_df = daily_enriched_df.copy()
    if start_date and end_date and not daily_enriched_df.empty:
        filtered_df = daily_enriched_df[
            (daily_enriched_df['date'] >= start_date) & 
            (daily_enriched_df['date'] <= end_date)
        ]
    
    if filtered_df.empty:
        empty_fig = create_empty_chart("No data available for selected range")
        return empty_fig, empty_fig, empty_fig
    
    # Create main chart based on type
    if chart_type == 'daily_energy':
        main_fig = create_daily_energy_chart(filtered_df, options)
    elif chart_type == 'daily_cost':
        main_fig = create_daily_cost_chart(filtered_df, options)
    elif chart_type == 'rate_analysis':
        main_fig = create_rate_analysis_chart(filtered_df, options)
    elif chart_type == 'net_flow':
        main_fig = create_net_flow_chart(filtered_df, options)
    else:
        main_fig = create_empty_chart("Chart type not implemented")
    
    # Create secondary charts
    balance_fig = create_energy_balance_chart(filtered_df)
    cost_fig = create_cost_breakdown_chart(filtered_df)
    
    return main_fig, balance_fig, cost_fig

def create_daily_energy_chart(df, options):
    """Create daily energy chart from enriched data"""
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    fig = go.Figure()
    
    if not import_data.empty:
        fig.add_trace(go.Scatter(
            x=import_data['date'],
            y=import_data['total_kwh'],
            mode='lines+markers',
            name='Grid Import',
            line=dict(color=colors['import'], width=3),
            hovertemplate='<b>Grid Import</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<br>Cost: £%{customdata:.2f}<extra></extra>',
            customdata=import_data['total_cost_pounds']
        ))
    
    if not export_data.empty:
        fig.add_trace(go.Scatter(
            x=export_data['date'],
            y=export_data['total_kwh'],
            mode='lines+markers',
            name='Solar Export',
            line=dict(color=colors['export'], width=3),
            hovertemplate='<b>Solar Export</b><br>Date: %{x}<br>Energy: %{y:.2f} kWh<br>Earnings: £%{customdata:.2f}<extra></extra>',
            customdata=export_data['cost_pounds']
        ))
    
    fig.update_layout(
        title='Daily Energy Overview (Bill-Accurate)',
        xaxis_title='Date',
        yaxis_title='Energy (kWh)',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="right", x=1)
    )
    
    return fig

def create_daily_cost_chart(df, options):
    """Create daily cost chart from enriched data"""
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    fig = go.Figure()
    
    if not import_data.empty:
        fig.add_trace(go.Scatter(
            x=import_data['date'],
            y=import_data['total_cost_pounds'],
            mode='lines+markers',
            name='Daily Bill (inc. standing charge)',
            line=dict(color=colors['import'], width=3),
            hovertemplate='<b>Daily Bill</b><br>Date: %{x}<br>Total: £%{y:.2f}<br>Energy: %{customdata:.2f} kWh<extra></extra>',
            customdata=import_data['total_kwh']
        ))
    
    if not export_data.empty:
        fig.add_trace(go.Scatter(
            x=export_data['date'],
            y=export_data['cost_pounds'],
            mode='lines+markers',
            name='Solar Export Earnings',
            line=dict(color=colors['export'], width=3),
            hovertemplate='<b>Export Earnings</b><br>Date: %{x}<br>Earnings: £%{y:.2f}<br>Energy: %{customdata:.2f} kWh<extra></extra>',
            customdata=export_data['total_kwh']
        ))
    
    fig.update_layout(
        title='Daily Costs & Earnings (Bill-Accurate)',
        xaxis_title='Date',
        yaxis_title='Cost (£)',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="right", x=1)
    )
    
    return fig

def create_rate_analysis_chart(df, options):
    """Create rate analysis chart showing tariff variations"""
    import_data = df[df['meter_type'] == 'import']
    
    if import_data.empty:
        return create_empty_chart("No import data available")
    
    fig = go.Figure()
    
    # Show rate ranges over time
    fig.add_trace(go.Scatter(
        x=import_data['date'],
        y=import_data['avg_rate'],
        mode='lines+markers',
        name='Average Rate',
        line=dict(color=colors['primary'], width=3),
        hovertemplate='<b>Average Rate</b><br>Date: %{x}<br>Rate: %{y:.2f}p/kWh<br>Tariff: %{customdata}<extra></extra>',
        customdata=import_data['tariff_code']
    ))
    
    # Add rate range bands
    fig.add_trace(go.Scatter(
        x=import_data['date'],
        y=import_data['max_rate'],
        mode='lines',
        name='Max Rate (Day)',
        line=dict(color=colors['danger'], width=1, dash='dash'),
        opacity=0.7
    ))
    
    fig.add_trace(go.Scatter(
        x=import_data['date'],
        y=import_data['min_rate'],
        mode='lines',
        name='Min Rate (Night)',
        line=dict(color=colors['success'], width=1, dash='dash'),
        opacity=0.7,
        fill='tonexty',
        fillcolor='rgba(0,0,255,0.1)'
    ))
    
    fig.update_layout(
        title='Energy Rate Analysis Over Time',
        xaxis_title='Date',
        yaxis_title='Rate (p/kWh)',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="right", x=1)
    )
    
    return fig

def create_net_flow_chart(df, options):
    """Create net energy flow chart"""
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
    
    # Create colors based on positive/negative flow
    colors_net = ['red' if x > 0 else 'green' for x in pivot_df['net_flow']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=pivot_df['date'],
        y=pivot_df['net_flow'],
        marker_color=colors_net,
        name='Net Energy Flow',
        hovertemplate='<b>Net Flow</b><br>Date: %{x}<br>Net: %{y:.2f} kWh<br><i>Positive = Net Import, Negative = Net Export</i><extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    
    fig.update_layout(
        title='Net Energy Flow (Import - Export)',
        xaxis_title='Date',
        yaxis_title='Net Energy (kWh)',
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
    total_import = df[df['meter_type'] == 'import']['total_kwh'].sum()
    total_export = df[df['meter_type'] == 'export']['total_kwh'].sum()
    
    fig = go.Figure(data=[go.Pie(
        labels=['Grid Import', 'Solar Export'],
        values=[total_import, total_export],
        hole=0.4,
        marker_colors=[colors['import'], colors['export']],
        hovertemplate='<b>%{label}</b><br>Energy: %{value:.1f} kWh<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title='Energy Balance Overview',
        template='plotly_white',
        annotations=[dict(text=f'{total_import + total_export:.1f}<br>Total kWh', 
                         x=0.5, y=0.5, font_size=14, showarrow=False)]
    )
    
    return fig

def create_cost_breakdown_chart(df):
    """Create cost breakdown pie chart"""
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    import_cost = import_data['cost_pounds'].sum() if not import_data.empty else 0
    standing_charges = import_data['standing_charge_pounds'].sum() if not import_data.empty else 0
    export_earnings = export_data['cost_pounds'].sum() if not export_data.empty else 0
    
    fig = go.Figure(data=[go.Pie(
        labels=['Energy Costs', 'Standing Charges', 'Export Earnings'],
        values=[import_cost, standing_charges, export_earnings],
        hole=0.4,
        marker_colors=[colors['import'], colors['warning'], colors['export']],
        hovertemplate='<b>%{label}</b><br>Amount: £%{value:.2f}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    net_cost = (import_cost + standing_charges) - export_earnings
    
    fig.update_layout(
        title='Cost Breakdown',
        template='plotly_white',
        annotations=[dict(text=f'Net Cost<br>£{net_cost:.2f}', 
                         x=0.5, y=0.5, font_size=14, showarrow=False)]
    )
    
    return fig

def create_empty_chart(message):
    """Create an empty chart with a message"""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
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
    print("🚀 Starting Simplified Solar Dashboard...")
    print("📊 Using enriched data with bill-accurate pricing...")
    print(f"   - Daily enriched data: {len(daily_enriched_df)} records")
    print(f"   - Total bill: £{enriched_stats.get('total_bill', 0):.2f}")
    print(f"   - Solar savings: {enriched_stats.get('solar_savings_rate', 0):.1f}%")
    print("🌐 Dashboard will be available at: http://127.0.0.1:8051")
    
    app.run(debug=True, host='127.0.0.1', port=8051) 