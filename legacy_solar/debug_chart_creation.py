import pandas as pd
import plotly.graph_objects as go
import json

# Load and process data exactly like unified dashboard
df = pd.read_csv('octopus_consumption_daily.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

# Filter to last 30 days
end_date = df['date'].max()
start_date = end_date - pd.Timedelta(days=30)
filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

print("=== CHART DATA PREPARATION ===")

# Recreate the exact chart creation logic
import_data = filtered_df[filtered_df['meter_type'] == 'import']
export_data = filtered_df[filtered_df['meter_type'] == 'export']

print("Import data for chart:")
print(f"Dates: {import_data['date'].tolist()[:5]}...")
print(f"Values: {import_data['total_kwh'].tolist()[:5]}...")
print(f"Total import data points: {len(import_data)}")

print("\nExport data for chart:")
print(f"Dates: {export_data['date'].tolist()[:5]}...")
print(f"Values: {export_data['total_kwh'].tolist()[:5]}...")
print(f"Total export data points: {len(export_data)}")

# Test rolling averages function
def add_rolling_averages(df, window=7):
    df_copy = df.copy()
    df_copy = df_copy.sort_values('date')
    
    for meter_type in df_copy['meter_type'].unique():
        mask = df_copy['meter_type'] == meter_type
        df_copy.loc[mask, 'rolling_avg'] = df_copy.loc[mask, 'total_kwh'].rolling(window=window, center=True).mean()
    
    return df_copy

print("\n=== TESTING ROLLING AVERAGES CHART DATA ===")
df_with_rolling = add_rolling_averages(filtered_df)
import_data_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'import']
export_data_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'export']

print("Import rolling averages:")
print(f"Dates: {import_data_rolling['date'].tolist()[:5]}...")
print(f"Original values: {import_data_rolling['total_kwh'].tolist()[:5]}...")
print(f"Rolling avg values: {import_data_rolling['rolling_avg'].tolist()[:5]}...")

# Create the chart exactly like unified dashboard
colors = {
    'import': '#dc3545',  # Red
    'export': '#28a745'   # Green
}

fig = go.Figure()

# Add rolling average traces (like unified dashboard does)
if not import_data_rolling.empty:
    print("\n=== ADDING IMPORT ROLLING AVG TRACE ===")
    print(f"X values (dates): {import_data_rolling['date'].tolist()[:3]}")
    print(f"Y values (rolling_avg): {import_data_rolling['rolling_avg'].tolist()[:3]}")
    
    fig.add_trace(go.Scatter(
        x=import_data_rolling['date'],
        y=import_data_rolling['rolling_avg'],
        mode='lines',
        name='Import (7-day avg)',
        line=dict(color=colors['import'], width=3)
    ))

if not export_data_rolling.empty:
    print("\n=== ADDING EXPORT ROLLING AVG TRACE ===")
    print(f"X values (dates): {export_data_rolling['date'].tolist()[:3]}")
    print(f"Y values (rolling_avg): {export_data_rolling['rolling_avg'].tolist()[:3]}")
    
    fig.add_trace(go.Scatter(
        x=export_data_rolling['date'],
        y=export_data_rolling['rolling_avg'],
        mode='lines',
        name='Export (7-day avg)',
        line=dict(color=colors['export'], width=3)
    ))

# Add original data as lighter traces
if not import_data.empty:
    print("\n=== ADDING IMPORT DAILY TRACE ===")
    print(f"X values (dates): {import_data['date'].tolist()[:3]}")
    print(f"Y values (total_kwh): {import_data['total_kwh'].tolist()[:3]}")
    
    fig.add_trace(go.Scatter(
        x=import_data['date'],
        y=import_data['total_kwh'],
        mode='lines',
        name='Grid Import (daily)',
        line=dict(color=colors['import'], width=1, dash='dot'),
        opacity=0.4
    ))

if not export_data.empty:
    print("\n=== ADDING EXPORT DAILY TRACE ===")
    print(f"X values (dates): {export_data['date'].tolist()[:3]}")
    print(f"Y values (total_kwh): {export_data['total_kwh'].tolist()[:3]}")
    
    fig.add_trace(go.Scatter(
        x=export_data['date'],
        y=export_data['total_kwh'],
        mode='lines',
        name='Solar Export (daily)',
        line=dict(color=colors['export'], width=1, dash='dot'),
        opacity=0.4
    ))

print("\n=== FINAL CHART INFO ===")
print(f"Number of traces: {len(fig.data)}")
for i, trace in enumerate(fig.data):
    print(f"Trace {i}: {trace.name}")
    print(f"  X values: {trace.x[:3] if len(trace.x) > 0 else 'None'}")
    print(f"  Y values: {trace.y[:3] if len(trace.y) > 0 else 'None'}")

# Save chart as JSON to compare
chart_json = fig.to_json()
print(f"\nChart JSON length: {len(chart_json)}")

# Check if values are cumulative somehow
if len(fig.data) > 0:
    first_trace = fig.data[0]
    if hasattr(first_trace, 'y') and len(first_trace.y) > 5:
        y_values = list(first_trace.y[:10])
        print(f"\nFirst 10 Y values from first trace: {y_values}")
        
        # Check if they're monotonically increasing (indicating cumsum)
        is_monotonic = all(i <= j for i, j in zip(y_values, y_values[1:]))
        print(f"Values are monotonically increasing: {is_monotonic}") 