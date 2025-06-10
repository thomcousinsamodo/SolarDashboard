#!/usr/bin/env python3
"""
Weather Data Integration for Solar Dashboard
Fetches historical weather data to correlate with solar generation
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Dict, Optional
import time
import numpy as np


class WeatherDataAPI:
    """Class to fetch historical weather data"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather API client
        Uses OpenWeatherMap API for historical data
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
        
    def fetch_historical_weather(self, lat: float, lon: float, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical weather data for date range
        
        Args:
            lat: Latitude
            lon: Longitude  
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with daily weather data
        """
        if not self.api_key or self.api_key == 'your_api_key_here':
            print("⚠️  OpenWeather API key not found. Using sample data...")
            return self.create_sample_weather_data(start_date, end_date)
        
        weather_data = []
        current_date = start_date
        
        print(f"🌤️  Fetching weather data from {start_date.date()} to {end_date.date()}...")
        
        while current_date <= end_date:
            try:
                timestamp = int(current_date.timestamp())
                
                params = {
                    'lat': lat,
                    'lon': lon,
                    'dt': timestamp,
                    'appid': self.api_key,
                    'units': 'metric'
                }
                
                response = requests.get(self.base_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    daily_data = data.get('data', [{}])[0]
                    
                    weather_record = {
                        'date': current_date.date(),
                        'temperature_avg': daily_data.get('temp', 15),
                        'temperature_max': daily_data.get('temp', 20),
                        'temperature_min': daily_data.get('temp', 10),
                        'humidity': daily_data.get('humidity', 70),
                        'cloud_cover': daily_data.get('clouds', 50),
                        'sunshine_hours': max(0, 10 - (daily_data.get('clouds', 50) / 10)),
                        'weather_description': daily_data.get('weather', [{}])[0].get('description', 'clear sky')
                    }
                    
                    weather_data.append(weather_record)
                    
                else:
                    print(f"⚠️  API error for {current_date.date()}: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  Error fetching weather for {current_date.date()}: {e}")
            
            current_date += timedelta(days=1)
            time.sleep(0.1)  # Rate limiting
        
        if weather_data:
            return pd.DataFrame(weather_data)
        else:
            return self.create_sample_weather_data(start_date, end_date)
    
    def create_sample_weather_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Create realistic sample weather data for demo purposes"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Create seasonal temperature pattern for Chesterfield/Derbyshire climate
        day_of_year = date_range.dayofyear
        # Slightly cooler base temperature for northern England (Derbyshire)
        base_temp = 12 + 8 * np.sin(2 * np.pi * (day_of_year - 80) / 365)  # Seasonal pattern
        
        weather_data = []
        for i, date in enumerate(date_range):
            # Add some randomness but realistic patterns
            temp_variation = np.random.normal(0, 3)
            cloud_variation = np.random.uniform(0, 100)
            
            avg_temp = base_temp[i] + temp_variation
            max_temp = avg_temp + np.random.uniform(2, 8)
            min_temp = avg_temp - np.random.uniform(2, 6)
            
            # More cloudy conditions typical for Derbyshire
            cloud_cover = max(0, min(100, cloud_variation + 15))  # Base +15% cloudiness
            sunshine_hours = max(0, 10 - (cloud_cover / 10))  # Reduced max sunshine for northern England
            
            weather_record = {
                'date': date.date(),
                'temperature_avg': round(avg_temp, 1),
                'temperature_max': round(max_temp, 1),
                'temperature_min': round(min_temp, 1),
                'humidity': round(np.random.uniform(40, 85), 1),
                'cloud_cover': round(cloud_cover, 1),
                'sunshine_hours': round(sunshine_hours, 1),
                'weather_description': f'Simulated data for {DEFAULT_LOCATION["name"]}'
            }
            
            weather_data.append(weather_record)
        
        return pd.DataFrame(weather_data)


def correlate_weather_solar(solar_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create weather correlation data for solar export
    """
    if solar_df.empty:
        return pd.DataFrame()
    
    # Get export data only
    export_df = solar_df[solar_df['meter_type'] == 'export'].copy()
    
    if export_df.empty:
        return pd.DataFrame()
    
    # Get date range
    start_date = pd.to_datetime(export_df['date']).min()
    end_date = pd.to_datetime(export_df['date']).max()
    
    # Create weather data
    weather_api = WeatherDataAPI()
    weather_df = weather_api.create_sample_weather_data(start_date, end_date)
    
    # Ensure date columns are the same type
    export_df['date'] = pd.to_datetime(export_df['date']).dt.date
    weather_df['date'] = pd.to_datetime(weather_df['date']).dt.date
    
    # Merge datasets
    combined_df = pd.merge(
        export_df[['date', 'total_kwh']], 
        weather_df, 
        on='date', 
        how='inner'
    )
    
    return combined_df


def create_weather_solar_chart(combined_df: pd.DataFrame, use_rolling_avg=False):
    """Create chart showing weather vs solar correlation"""
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots
    
    if combined_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No weather data available for correlation",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Create subplot with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Sort data by date for rolling averages
    combined_df = combined_df.sort_values('date')
    
    # Calculate rolling averages if requested
    if use_rolling_avg:
        # Calculate rolling window based on data range
        date_range_days = (pd.to_datetime(combined_df['date']).max() - pd.to_datetime(combined_df['date']).min()).days
        
        if date_range_days < 90:
            window = 7
        elif date_range_days < 365:
            window = 14
        else:
            window = 30
            
        # Add rolling averages
        combined_df['solar_rolling'] = combined_df['total_kwh'].rolling(window=window, center=True).mean()
        combined_df['temp_rolling'] = combined_df['temperature_avg'].rolling(window=window, center=True).mean()
        combined_df['sunshine_rolling'] = combined_df['sunshine_hours'].rolling(window=window, center=True).mean()
        
        # Solar export - original data (lighter) and rolling average (bold)
        fig.add_trace(
            go.Bar(
                x=combined_df['date'],
                y=combined_df['total_kwh'],
                name='Solar Export (daily)',
                marker_color='green',
                opacity=0.3
            ),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['solar_rolling'],
                mode='lines',
                name=f'Solar Export ({window}-day avg)',
                line=dict(color='darkgreen', width=3)
            ),
            secondary_y=False,
        )
        
        # Temperature - original data (lighter) and rolling average (bold)
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['temperature_avg'],
                mode='lines',
                name='Temperature (daily)',
                line=dict(color='red', width=1, dash='dot'),
                opacity=0.4
            ),
            secondary_y=True,
        )
        
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['temp_rolling'],
                mode='lines',
                name=f'Temperature ({window}-day avg)',
                line=dict(color='red', width=2)
            ),
            secondary_y=True,
        )
        
        # Sunshine hours - original data (lighter) and rolling average (bold)
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['sunshine_hours'],
                mode='lines',
                name='Sunshine Hours (daily)',
                line=dict(color='orange', width=1, dash='dot'),
                opacity=0.4
            ),
            secondary_y=True,
        )
        
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['sunshine_rolling'],
                mode='lines',
                name=f'Sunshine Hours ({window}-day avg)',
                line=dict(color='darkorange', width=2)
            ),
            secondary_y=True,
        )
        
        title = f'Solar Generation vs Weather Conditions ({window}-day Rolling Average)'
    else:
        # Standard chart without rolling averages
        # Solar export bar chart
        fig.add_trace(
            go.Bar(
                x=combined_df['date'],
                y=combined_df['total_kwh'],
                name='Solar Export (kWh)',
                marker_color='green',
                opacity=0.7
            ),
            secondary_y=False,
        )
        
        # Temperature line
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['temperature_avg'],
                mode='lines',
                name='Temperature (°C)',
                line=dict(color='red', width=2)
            ),
            secondary_y=True,
        )
        
        # Sunshine hours line
        fig.add_trace(
            go.Scatter(
                x=combined_df['date'],
                y=combined_df['sunshine_hours'],
                mode='lines',
                name='Sunshine Hours',
                line=dict(color='orange', width=2)
            ),
            secondary_y=True,
        )
        
        title = 'Solar Generation vs Weather Conditions'
    
    # Update layout
    fig.update_layout(
        title=title,
        template='plotly_white',
        hovermode='x unified'
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Solar Export (kWh)", secondary_y=False)
    fig.update_yaxes(title_text="Temperature (°C) / Sunshine Hours", secondary_y=True)
    
    return fig


def get_weather_correlation_stats(combined_df: pd.DataFrame) -> Dict:
    """Calculate correlation statistics"""
    if combined_df.empty or len(combined_df) < 2:
        return {}
    
    correlations = {
        'temperature_correlation': combined_df['total_kwh'].corr(combined_df['temperature_avg']),
        'sunshine_correlation': combined_df['total_kwh'].corr(combined_df['sunshine_hours']),
        'cloud_correlation': combined_df['total_kwh'].corr(combined_df['cloud_cover'])
    }
    
    return correlations


# Default coordinates (S40 2EG - Chesterfield, Derbyshire)
DEFAULT_LOCATION = {
    'lat': 53.2514,  # Chesterfield latitude
    'lon': -1.4210,  # Chesterfield longitude  
    'name': 'Chesterfield, Derbyshire (S40 2EG)'
}


def get_weather_for_solar_data(solar_df: pd.DataFrame, location: Dict = None) -> pd.DataFrame:
    """
    Main function to get weather data for solar analysis
    
    Args:
        solar_df: Daily solar data
        location: Dict with lat, lon, name (optional)
        
    Returns:
        Combined DataFrame with weather and solar data
    """
    if location is None:
        location = DEFAULT_LOCATION
    
    if solar_df.empty:
        print("❌ No solar data provided")
        return pd.DataFrame()
    
    # Get date range from solar data
    start_date = pd.to_datetime(solar_df['date']).min()
    end_date = pd.to_datetime(solar_df['date']).max()
    
    print(f"🌍 Fetching weather data for {location.get('name', 'your location')}")
    print(f"📅 Date range: {start_date.date()} to {end_date.date()}")
    
    # Initialize weather API
    weather_api = WeatherDataAPI()
    
    # Fetch weather data
    weather_df = weather_api.fetch_historical_weather(
        location['lat'], 
        location['lon'], 
        start_date, 
        end_date
    )
    
    # Correlate with solar data
    combined_df = correlate_weather_solar(solar_df)
    
    return combined_df 