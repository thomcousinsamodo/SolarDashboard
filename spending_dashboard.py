#!/usr/bin/env python3
"""
Spending Dashboard for OctopusTracker
Combines consumption data with tariff rates to show actual spending and earnings.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import database_utils
import credential_manager
import logging
from plotly.subplots import make_subplots

app = Flask(__name__)
app.secret_key = 'octopus-spending-dashboard-secret'

def load_spending_data(start_date=None, end_date=None):
    """Load and combine consumption and pricing data to calculate spending."""
    
    # Load consumption data (half-hourly)
    consumption_df = database_utils.load_consumption_data(
        start_date=start_date, 
        end_date=end_date, 
        table_name='consumption_raw'
    )
    
    if consumption_df.empty:
        return pd.DataFrame()
    
    # Convert datetime columns and normalize timezone
    consumption_df['interval_start'] = pd.to_datetime(consumption_df['interval_start'], utc=True)
    consumption_df['interval_end'] = pd.to_datetime(consumption_df['interval_end'], utc=True)
    
    # Load pricing data
    pricing_df = database_utils.load_pricing_data(
        start_date=start_date,
        end_date=end_date
    )
    
    if pricing_df.empty:
        print("Warning: No pricing data found")
        return pd.DataFrame()
    
    # Convert pricing datetime and normalize timezone to UTC
    pricing_df['datetime'] = pd.to_datetime(pricing_df['datetime'], utc=True)
    
    # Filter pricing data to only include records with actual rates
    pricing_df = pricing_df[pricing_df['rate_inc_vat'].notna()].copy()
    
    if pricing_df.empty:
        print("Warning: No pricing data with rates found")
        return pd.DataFrame()
    
    # Prepare data for joining
    results = []
    
    # Process each meter type separately
    for meter_type in ['import', 'export']:
        # Get consumption for this meter type
        meter_consumption = consumption_df[consumption_df['meter_type'] == meter_type].copy()
        
        if meter_consumption.empty:
            continue
        
        # Get pricing for this flow direction
        meter_pricing = pricing_df[pricing_df['flow_direction'] == meter_type].copy()
        
        if meter_pricing.empty:
            print(f"Warning: No pricing data for {meter_type}")
            continue
        
        # Merge on datetime - using interval_start for consumption and datetime for pricing
        # Both are now in UTC timezone
        merged = pd.merge_asof(
            meter_consumption.sort_values('interval_start'),
            meter_pricing.sort_values('datetime'),
            left_on='interval_start',
            right_on='datetime',
            direction='backward',  # Use the most recent pricing data
            suffixes=('', '_pricing')
        )
        
        # Calculate cost/earnings
        merged['rate_pence_per_kwh'] = merged['rate_inc_vat']  # Already in pence
        merged['cost_pence'] = merged['consumption'] * merged['rate_pence_per_kwh']
        merged['cost_pounds'] = merged['cost_pence'] / 100
        
        results.append(merged)
    
    if not results:
        return pd.DataFrame()
    
    # Combine all results
    combined_df = pd.concat(results, ignore_index=True)
    
    # Sort by datetime
    combined_df = combined_df.sort_values('interval_start').reset_index(drop=True)
    
    return combined_df

def calculate_spending_summary(df):
    """Calculate summary statistics for spending."""
    if df.empty:
        return {
            'total_import_cost': 0,
            'total_export_earnings': 0,
            'net_cost': 0,
            'total_import_kwh': 0,
            'total_export_kwh': 0,
            'avg_import_rate': 0,
            'avg_export_rate': 0,
            'period_days': 0,
            'total_standing_charges': 0
        }
    
    # Load standing charges
    standing_charges_df = load_standing_charges()
    
    # Separate import and export
    import_data = df[df['meter_type'] == 'import']
    export_data = df[df['meter_type'] == 'export']
    
    # Calculate basic energy costs (usage only)
    usage_import_cost = import_data['cost_pounds'].sum() if not import_data.empty else 0
    total_export_earnings = export_data['cost_pounds'].sum() if not export_data.empty else 0
    
    # Calculate standing charges for the period
    total_standing_charges = 0
    standing_charge_days = 0
    if not df.empty:
        # Get unique dates in the period
        start_date = df['interval_start'].min().date()
        end_date = df['interval_start'].max().date()
        
        # Sum standing charges for each day in the period
        current_date = start_date
        while current_date <= end_date:
            daily_standing_charge = get_standing_charge_for_date(current_date, standing_charges_df)
            total_standing_charges += daily_standing_charge
            standing_charge_days += 1
            current_date += pd.Timedelta(days=1)
    
    # Total import cost including standing charges
    total_import_cost = usage_import_cost + total_standing_charges
    
    # Net cost (positive = you pay, negative = you earn)
    net_cost = total_import_cost - total_export_earnings
    
    # Energy totals
    total_import_kwh = import_data['consumption'].sum() if not import_data.empty else 0
    total_export_kwh = export_data['consumption'].sum() if not export_data.empty else 0
    
    # Average rates
    avg_import_rate = import_data['rate_pence_per_kwh'].mean() if not import_data.empty else 0
    avg_export_rate = export_data['rate_pence_per_kwh'].mean() if not export_data.empty else 0
    
    # Period calculation - use the same method as standing charges for consistency
    period_days = standing_charge_days
    
    return {
        'total_import_cost': total_import_cost,
        'usage_import_cost': usage_import_cost,
        'total_standing_charges': total_standing_charges,
        'avg_daily_standing_charge': total_standing_charges / period_days if period_days > 0 else 0,
        'total_export_earnings': total_export_earnings,
        'net_cost': net_cost,
        'total_import_kwh': total_import_kwh,
        'total_export_kwh': total_export_kwh,
        'avg_import_rate': avg_import_rate,
        'avg_export_rate': avg_export_rate,
        'period_days': period_days
    }

def create_spending_timeline_chart(df, show_markers=True, fill_areas=True):
    """Create a timeline chart showing spending/earnings over time."""
    if df.empty:
        return create_empty_chart("No spending data available")
    
    # Load standing charges
    standing_charges_df = load_standing_charges()
    
    # Group by day and meter type - ensure we get daily totals only
    daily_spending = df.groupby([df['interval_start'].dt.date, 'meter_type']).agg({
        'cost_pounds': 'sum',
        'consumption': 'sum'
    }).reset_index()
    
    # Convert the date column properly
    daily_spending['date'] = pd.to_datetime(daily_spending['interval_start'])
    
    # Add standing charges for each day (only for import costs)
    import_data = daily_spending[daily_spending['meter_type'] == 'import'].copy()
    if not import_data.empty:
        import_data['standing_charge'] = import_data['date'].apply(
            lambda date: get_standing_charge_for_date(date, standing_charges_df)
        )
        import_data['total_cost'] = import_data['cost_pounds'] + import_data['standing_charge']
    else:
        import_data = pd.DataFrame()
    
    fig = go.Figure()
    
    # Add export earnings (positive values on top)
    export_data = daily_spending[daily_spending['meter_type'] == 'export'].sort_values('date')
    if not export_data.empty:
        trace_mode = 'lines+markers' if show_markers else 'lines'
        fill_mode = 'tozeroy' if fill_areas else None
        fillcolor = 'rgba(40, 167, 69, 0.1)' if fill_areas else None
        
        fig.add_trace(go.Scatter(
            x=export_data['date'],
            y=export_data['cost_pounds'],  # Positive values for earnings (top of chart)
            mode=trace_mode,
            name='Daily Export Earnings',
            line=dict(color='#28a745', width=2),
            fill=fill_mode,
            fillcolor=fillcolor,
            hovertemplate='<b>Daily Export Earnings</b><br>' +
                         'Date: %{x}<br>' +
                         'Earnings: £%{y:.2f}<br>' +
                         '<extra></extra>'
        ))
    
    # Add standing charges baseline (negative values at bottom)
    if not import_data.empty:
        trace_mode = 'lines+markers' if show_markers else 'lines'
        fill_mode = 'tozeroy' if fill_areas else None
        fillcolor = 'rgba(255, 193, 7, 0.1)' if fill_areas else None
        
        fig.add_trace(go.Scatter(
            x=import_data['date'],
            y=-import_data['standing_charge'],  # Negative values for standing charges (bottom baseline)
            mode=trace_mode,
            name='Daily Standing Charges',
            line=dict(color='#ffc107', width=2),
            fill=fill_mode,
            fillcolor=fillcolor,
            hovertemplate='<b>Daily Standing Charges</b><br>' +
                         'Date: %{x}<br>' +
                         'Standing Charge: £%{y:.2f}<br>' +
                         '<extra></extra>'
        ))
    
    # Add import costs (negative values, stacked on standing charges)
    if not import_data.empty:
        trace_mode = 'lines+markers' if show_markers else 'lines'
        fill_mode = 'tonexty' if fill_areas else None  # Fill to next y (standing charges)
        fillcolor = 'rgba(220, 53, 69, 0.1)' if fill_areas else None
        
        fig.add_trace(go.Scatter(
            x=import_data['date'],
            y=-import_data['total_cost'],  # Negative total costs (standing charges + usage costs)
            mode=trace_mode,
            name='Daily Total Import Costs',
            line=dict(color='#dc3545', width=2),
            fill=fill_mode,
            fillcolor=fillcolor,
            hovertemplate='<b>Daily Total Import Costs</b><br>' +
                         'Date: %{x}<br>' +
                         'Usage Cost: £%{customdata[0]:.2f}<br>' +
                         'Standing Charge: £%{customdata[1]:.2f}<br>' +
                         'Total: £%{customdata[2]:.2f}<br>' +
                         '<extra></extra>',
            customdata=list(zip(import_data['cost_pounds'], import_data['standing_charge'], import_data['total_cost']))
        ))
    
    # Calculate and add net position line
    # Create a proper pivot table to align dates
    net_daily = daily_spending.pivot(index='date', columns='meter_type', values='cost_pounds').fillna(0)
    
    # Add standing charges to import costs if we have import data
    if not import_data.empty and 'import' in net_daily.columns:
        # Create a dataframe for standing charges aligned with dates
        standing_charges_by_date = import_data.set_index('date')['standing_charge']
        # Add standing charges to import costs
        net_daily['import'] = net_daily['import'] + standing_charges_by_date.reindex(net_daily.index, fill_value=0)
    
    # Calculate daily net position (export earnings - total import costs including standing charges)
    if 'import' in net_daily.columns and 'export' in net_daily.columns:
        net_daily['net'] = net_daily['export'] - net_daily['import']
    elif 'import' in net_daily.columns:
        net_daily['net'] = -net_daily['import']
    elif 'export' in net_daily.columns:
        net_daily['net'] = net_daily['export']
    else:
        net_daily['net'] = 0
    
    # Reset index to get dates as a column
    net_daily_reset = net_daily.reset_index()
    
    net_trace_mode = 'lines+markers' if show_markers else 'lines'
    fig.add_trace(go.Scatter(
        x=net_daily_reset['date'],
        y=net_daily_reset['net'],  # Net position (positive = earning more than spending)
        mode=net_trace_mode,
        name='Daily Net Position',
        line=dict(color='#007bff', width=1.5),
        hovertemplate='<b>Daily Net Position</b><br>' +
                     'Date: %{x}<br>' +
                     'Net: £%{y:.2f}<br>' +
                     '<extra></extra>'
    ))
    
    # Add horizontal line at zero
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    # Update layout with flipped axis labels
    fig.update_layout(
        title='Daily Energy Spending & Earnings',
        xaxis_title='Date',
        yaxis_title='Daily Amount (£)',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[
            dict(
                text="Earnings (positive)",
                xref="paper", yref="paper",
                x=0.02, y=0.95,
                xanchor='left', yanchor='top',
                showarrow=False,
                font=dict(size=12, color="#28a745"),
                bgcolor="rgba(255,255,255,0.8)"
            ),
            dict(
                text="Costs (negative)",
                xref="paper", yref="paper",
                x=0.02, y=0.05,
                xanchor='left', yanchor='bottom',
                showarrow=False,
                font=dict(size=12, color="#dc3545"),
                bgcolor="rgba(255,255,255,0.8)"
            )
        ]
    )
    
    # Fix binary data encoding issues that cause display problems
    chart_dict = fig.to_dict()
    fixed_chart = fix_chart_binary_data(chart_dict)
    return json.dumps(fixed_chart, cls=PlotlyJSONEncoder)

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

def create_hourly_spending_chart(df):
    """Create a chart showing average spending by hour of day."""
    if df.empty:
        return create_empty_chart("No spending data available")
    
    # Extract hour from interval_start
    df_copy = df.copy()
    df_copy['hour'] = df_copy['interval_start'].dt.hour
    
    # Group by hour and meter type
    hourly_spending = df_copy.groupby(['hour', 'meter_type']).agg({
        'cost_pounds': 'mean',
        'rate_pence_per_kwh': 'mean',
        'consumption': 'mean'
    }).reset_index()
    
    fig = go.Figure()
    
    # Add import costs
    import_data = hourly_spending[hourly_spending['meter_type'] == 'import']
    if not import_data.empty:
        fig.add_trace(go.Bar(
            x=import_data['hour'],
            y=import_data['cost_pounds'],
            name='Avg Import Cost',
            marker_color='#dc3545',
            hovertemplate='<b>Hour %{x}:00</b><br>' +
                         'Avg Import Cost: £%{y:.3f}<br>' +
                         '<extra></extra>'
        ))
    
    # Add export earnings
    export_data = hourly_spending[hourly_spending['meter_type'] == 'export']
    if not export_data.empty:
        fig.add_trace(go.Bar(
            x=export_data['hour'],
            y=-export_data['cost_pounds'],  # Negative to show below zero
            name='Avg Export Earnings',
            marker_color='#28a745',
            hovertemplate='<b>Hour %{x}:00</b><br>' +
                         'Avg Export Earnings: £%{y:.3f}<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title='Average Spending/Earnings by Hour of Day',
        xaxis_title='Hour of Day',
        yaxis_title='Average Cost (£)',
        xaxis=dict(tickmode='linear', dtick=2),
        template='plotly_white',
        height=400,
        showlegend=True,
        bargap=0.2
    )
    
    # Fix binary data encoding issues that cause display problems
    chart_dict = fig.to_dict()
    fixed_chart = fix_chart_binary_data(chart_dict)
    return json.dumps(fixed_chart, cls=PlotlyJSONEncoder)

def create_rate_comparison_chart(df):
    """Create a chart comparing import and export rates over time."""
    if df.empty:
        return create_empty_chart("No rate data available")
    
    # Sample data to avoid too many points
    df_sample = df.sample(min(1000, len(df))).sort_values('interval_start')
    
    fig = go.Figure()
    
    # Add import rates
    import_data = df_sample[df_sample['meter_type'] == 'import']
    if not import_data.empty:
        fig.add_trace(go.Scatter(
            x=import_data['interval_start'],
            y=import_data['rate_pence_per_kwh'],
            mode='markers',
            name='Import Rate',
            marker=dict(color='#dc3545', size=4, opacity=0.6),
            hovertemplate='<b>Import Rate</b><br>' +
                         'Time: %{x}<br>' +
                         'Rate: %{y:.2f}p/kWh<br>' +
                         '<extra></extra>'
        ))
    
    # Add export rates
    export_data = df_sample[df_sample['meter_type'] == 'export']
    if not export_data.empty:
        fig.add_trace(go.Scatter(
            x=export_data['interval_start'],
            y=export_data['rate_pence_per_kwh'],
            mode='markers',
            name='Export Rate',
            marker=dict(color='#28a745', size=4, opacity=0.6),
            hovertemplate='<b>Export Rate</b><br>' +
                         'Time: %{x}<br>' +
                         'Rate: %{y:.2f}p/kWh<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title='Import vs Export Rates Over Time',
        xaxis_title='Date/Time',
        yaxis_title='Rate (pence/kWh)',
        template='plotly_white',
        height=400,
        showlegend=True,
        hovermode='x unified'
    )
    
    # Fix binary data encoding issues that cause display problems
    chart_dict = fig.to_dict()
    fixed_chart = fix_chart_binary_data(chart_dict)
    return json.dumps(fixed_chart, cls=PlotlyJSONEncoder)

def create_hourly_price_usage_chart(df):
    """Create a chart showing average tariff rates by hour with consumption overlay."""
    if df.empty:
        return create_empty_chart("No data available for hourly analysis")
    
    # Extract hour from interval_start
    df_copy = df.copy()
    df_copy['hour'] = df_copy['interval_start'].dt.hour
    
    # Group by hour and meter type to get averages - focus only on import data
    hourly_data = df_copy.groupby(['hour', 'meter_type']).agg({
        'rate_pence_per_kwh': 'mean',
        'consumption': 'mean'
    }).reset_index()
    
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add import rate line (primary y-axis)
    import_data = hourly_data[hourly_data['meter_type'] == 'import']
    if not import_data.empty:
        fig.add_trace(
            go.Scatter(
                x=import_data['hour'],
                y=import_data['rate_pence_per_kwh'],
                mode='lines+markers',
                name='Avg Import Rate',
                line=dict(color='#dc3545', width=3),
                marker=dict(size=8),
                hovertemplate='<b>Hour %{x}:00</b><br>' +
                             'Avg Import Rate: %{y:.2f}p/kWh<br>' +
                             '<extra></extra>'
            ),
            secondary_y=False
        )
        
        # Add import consumption bars (secondary y-axis)
        fig.add_trace(
            go.Bar(
                x=import_data['hour'],
                y=import_data['consumption'],
                name='Avg Import Usage',
                marker_color='rgba(220, 53, 69, 0.3)',
                yaxis='y2',
                hovertemplate='<b>Hour %{x}:00</b><br>' +
                             'Avg Import Usage: %{y:.3f} kWh<br>' +
                             '<extra></extra>'
            ),
            secondary_y=True
        )
    
    # Update layout
    fig.update_layout(
        title='Average Import Rates vs Your Energy Usage by Hour of Day',
        xaxis_title='Hour of Day',
        template='plotly_white',
        height=500,
        showlegend=True,
        hovermode='x unified',
        xaxis=dict(tickmode='linear', dtick=2, range=[-0.5, 23.5])
    )
    
    # Set y-axes titles
    fig.update_yaxes(title_text='Import Rate (pence/kWh)', secondary_y=False)
    fig.update_yaxes(title_text='Energy Usage (kWh)', secondary_y=True)
    
    # Fix binary data encoding issues that cause display problems
    chart_dict = fig.to_dict()
    fixed_chart = fix_chart_binary_data(chart_dict)
    return json.dumps(fixed_chart, cls=PlotlyJSONEncoder)

def create_empty_chart(message):
    """Create an empty chart with a message."""
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
        height=400,
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False)
    )
    # Fix binary data encoding issues that cause display problems
    chart_dict = fig.to_dict()
    fixed_chart = fix_chart_binary_data(chart_dict)
    return json.dumps(fixed_chart, cls=PlotlyJSONEncoder)

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
            # Convert from pence to pounds
            df['daily_charge_pounds'] = df['value_inc_vat'] / 100
            
        return df
        
    except Exception as e:
        logger.error(f"Error loading standing charges: {e}")
        return pd.DataFrame()

def get_standing_charge_for_date(date_str, standing_charges_df):
    """Get the standing charge that applies to a specific date."""
    if standing_charges_df.empty:
        return 0.0
    
    date = pd.to_datetime(date_str)
    
    # Find the standing charge period that covers this date
    # Handle ongoing periods where end_date is null
    applicable = standing_charges_df[
        (standing_charges_df['start_date'] <= date) & 
        ((standing_charges_df['end_date'] >= date) | pd.isna(standing_charges_df['end_date']))
    ]
    
    if not applicable.empty:
        return applicable.iloc[0]['daily_charge_pounds']
    
    return 0.0

@app.route('/')
def spending_dashboard():
    """Main spending dashboard page."""
    # Default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Load spending data
    spending_df = load_spending_data(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    # Calculate summary
    summary = calculate_spending_summary(spending_df)
    
    # Check if we have data
    has_data = not spending_df.empty
    
    return render_template('spending.html', 
                         summary=summary,
                         has_data=has_data,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'))

@app.route('/api/spending-charts', methods=['POST'])
def api_spending_charts():
    """API endpoint to get spending charts."""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Get chart options
        show_markers = data.get('show_markers', True)
        fill_areas = data.get('fill_areas', True)
        
        # Load spending data
        spending_df = load_spending_data(start_date, end_date)
        
        if spending_df.empty:
            return jsonify({
                'success': False,
                'message': 'No spending data found for the selected period'
            })
        
        # Create charts with options
        timeline_chart = create_spending_timeline_chart(spending_df, show_markers=show_markers, fill_areas=fill_areas)
        hourly_chart = create_hourly_spending_chart(spending_df)
        hourly_price_usage_chart = create_hourly_price_usage_chart(spending_df)
        
        # Calculate updated summary
        summary = calculate_spending_summary(spending_df)
        
        return jsonify({
            'success': True,
            'charts': {
                'timeline': timeline_chart,
                'hourly': hourly_chart,
                'hourly_price_usage': hourly_price_usage_chart
            },
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("💰 Starting Octopus Energy Spending Dashboard...")
    print("🌐 Dashboard will be available at: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001) 