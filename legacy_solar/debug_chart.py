import pandas as pd
import json
from datetime import timedelta

# Load data exactly like unified dashboard
df = pd.read_csv('octopus_consumption_daily.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

print("=== RAW DATA SAMPLE ===")
print("Import data:")
import_sample = df[df['meter_type'] == 'import'].head(10)
print(import_sample[['date', 'total_kwh']])

print("\nExport data:")
export_sample = df[df['meter_type'] == 'export'].head(10)
print(export_sample[['date', 'total_kwh']])

# Filter to last 30 days like unified dashboard
print("\n=== FILTERING LIKE UNIFIED DASHBOARD ===")
end_date = df['date'].max()
start_date = end_date - pd.Timedelta(days=30)
filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

print(f"Date range: {start_date} to {end_date}")
print(f"Filtered data shape: {filtered_df.shape}")

print("\nFiltered import data:")
import_filtered = filtered_df[filtered_df['meter_type'] == 'import']
print(import_filtered[['date', 'total_kwh']])

print("\nFiltered export data:")
export_filtered = filtered_df[filtered_df['meter_type'] == 'export']
print(export_filtered[['date', 'total_kwh']])

# Test add_rolling_averages function
def add_rolling_averages(df, window=7):
    """Add rolling averages to the dataframe"""
    df_copy = df.copy()
    df_copy = df_copy.sort_values('date')
    
    for meter_type in df_copy['meter_type'].unique():
        mask = df_copy['meter_type'] == meter_type
        df_copy.loc[mask, 'rolling_avg'] = df_copy.loc[mask, 'total_kwh'].rolling(window=window, center=True).mean()
    
    return df_copy

print("\n=== TESTING ROLLING AVERAGES ===")
df_with_rolling = add_rolling_averages(filtered_df)

print("Import with rolling averages:")
import_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'import']
print(import_rolling[['date', 'total_kwh', 'rolling_avg']].head(10))

print("\nExport with rolling averages:")
export_rolling = df_with_rolling[df_with_rolling['meter_type'] == 'export']
print(export_rolling[['date', 'total_kwh', 'rolling_avg']].head(10))

# Check if any values look like cumulative or artificial increments
print("\n=== CHECKING FOR ARTIFICIAL INCREMENTS ===")
print("Import total_kwh differences:")
import_diffs = import_filtered['total_kwh'].diff()
print(import_diffs.head(10))

print("\nAre all differences around 1.0?", (import_diffs.abs() - 1.0).abs().mean() < 0.1)
print("Mean difference:", import_diffs.mean())
print("Std difference:", import_diffs.std()) 