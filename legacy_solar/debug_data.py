import pandas as pd
import numpy as np

# Load data the same way as unified dashboard
df = pd.read_csv('octopus_consumption_daily.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

print('Data structure:')
print(df.head(10))
print()

# Check import data specifically
import_data = df[df['meter_type'] == 'import'].head(10)
print('Import data sample:')
print(import_data[['date', 'total_kwh']])
print()

# Check if rolling averages cause cumulative effect
df_copy = df.copy()
df_copy = df_copy.sort_values('date')

for meter_type in df_copy['meter_type'].unique():
    mask = df_copy['meter_type'] == meter_type
    df_copy.loc[mask, 'rolling_avg'] = df_copy.loc[mask, 'total_kwh'].rolling(window=7, center=True).mean()

import_with_rolling = df_copy[df_copy['meter_type'] == 'import'].head(10)
print('Import data with rolling averages:')
print(import_with_rolling[['date', 'total_kwh', 'rolling_avg']])
print()

# Check export data
export_data = df[df['meter_type'] == 'export'].head(10)
print('Export data sample:')
print(export_data[['date', 'total_kwh']])
print()

# Check value ranges
import_all = df[df['meter_type'] == 'import']
export_all = df[df['meter_type'] == 'export'] 
print(f'Import total_kwh range: {import_all["total_kwh"].min():.2f} to {import_all["total_kwh"].max():.2f}')
print(f'Export total_kwh range: {export_all["total_kwh"].min():.2f} to {export_all["total_kwh"].max():.2f}')
print(f'Import data points: {len(import_all)}')
print(f'Export data points: {len(export_all)}') 