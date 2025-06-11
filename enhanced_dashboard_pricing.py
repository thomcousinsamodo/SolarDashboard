#!/usr/bin/env python3
"""
Enhanced dashboard pricing integration with tariff transitions and Agile pricing visualization.
"""

import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bill_accurate_pricing import BillAccuratePricingProcessor

class EnhancedDashboardPricing:
    """Enhanced pricing system for dashboard with transition marking and Agile support."""
    
    def __init__(self):
        """Initialize the enhanced pricing system."""
        self.bill_processor = BillAccuratePricingProcessor()
        self.colors = {
            'import': '#dc3545',
            'export': '#28a745',
            'price_line': '#17a2b8',
            'transition': '#ffc107',
            'agile': '#6f42c1'
        }
    
    def calculate_daily_costs(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate daily costs using bill-accurate pricing."""
        if daily_df.empty:
            return daily_df.copy()
        
        result_df = daily_df.copy()
        
        # Add cost columns
        result_df['cost_pence'] = 0.0
        result_df['cost_pounds'] = 0.0
        result_df['total_cost_pence'] = 0.0
        result_df['total_cost_pounds'] = 0.0
        result_df['standing_charge_pence'] = 0.0
        result_df['standing_charge_pounds'] = 0.0
        result_df['rate_pence_per_kwh'] = 0.0
        result_df['tariff_code'] = ''
        result_df['rate_type'] = ''
        
        for index, row in result_df.iterrows():
            date = row['date']
            meter_type = row['meter_type']
            total_kwh = row['total_kwh']
            
            # Convert date to datetime for tariff lookup
            if isinstance(date, str):
                lookup_date = pd.to_datetime(date)
            else:
                lookup_date = date
            
            # Find tariff period for this date
            tariff_period = self.bill_processor.find_tariff_period(lookup_date)
            
            if tariff_period is None:
                continue
            
            # For daily calculations, we need to estimate the distribution across day/night
            # This is a simplified approach - for exact calculations, we'd need half-hourly data
            if tariff_period['rate_type'] == 'time_of_use':
                # Get day and night rates
                day_rate = 0
                night_rate = 0
                for rate in tariff_period['time_of_use_rates']:
                    if rate['rate_name'] == 'Day':
                        day_rate = rate['rate_pence_per_kwh']
                    elif rate['rate_name'] == 'Night':
                        night_rate = rate['rate_pence_per_kwh']
                
                # Estimate 16 hours day (07:00-23:00) and 8 hours night (23:00-07:00)
                # Assume more consumption during day for typical household
                day_proportion = 0.7  # 70% of daily consumption during day hours
                night_proportion = 0.3  # 30% during night hours
                
                day_kwh = total_kwh * day_proportion
                night_kwh = total_kwh * night_proportion
                
                cost_pence = (day_kwh * day_rate) + (night_kwh * night_rate)
                avg_rate = cost_pence / total_kwh if total_kwh > 0 else 0
                rate_type_text = f"Day/Night (D:{day_rate:.2f}p N:{night_rate:.2f}p)"
                
            else:
                # Fixed rate
                rate = tariff_period['rate_pence_per_kwh']
                cost_pence = total_kwh * rate
                avg_rate = rate
                rate_type_text = f"Fixed ({rate:.2f}p)"
            
            # Calculate standing charge (only for import)
            standing_charge_pence = 0.0
            if meter_type == 'import':
                standing_charge_pence = tariff_period['standing_charge_pence_per_day']
            
            # Update result
            result_df.at[index, 'cost_pence'] = cost_pence
            result_df.at[index, 'cost_pounds'] = cost_pence / 100
            result_df.at[index, 'standing_charge_pence'] = standing_charge_pence
            result_df.at[index, 'standing_charge_pounds'] = standing_charge_pence / 100
            result_df.at[index, 'total_cost_pence'] = cost_pence + standing_charge_pence
            result_df.at[index, 'total_cost_pounds'] = (cost_pence + standing_charge_pence) / 100
            result_df.at[index, 'rate_pence_per_kwh'] = avg_rate
            result_df.at[index, 'tariff_code'] = tariff_period['tariff_code']
            result_df.at[index, 'rate_type'] = rate_type_text
        
        return result_df
    
    def get_summary_stats(self, daily_df: pd.DataFrame) -> Dict:
        """Calculate summary financial statistics using bill-accurate pricing."""
        df_with_costs = self.calculate_daily_costs(daily_df)
        
        if df_with_costs.empty:
            return {}
            
        import_data = df_with_costs[df_with_costs['meter_type'] == 'import']
        export_data = df_with_costs[df_with_costs['meter_type'] == 'export']
        
        total_import_cost = import_data['cost_pounds'].sum() if not import_data.empty else 0
        total_export_earnings = export_data['cost_pounds'].sum() if not export_data.empty else 0
        total_standing_charges = import_data['standing_charge_pounds'].sum() if not import_data.empty else 0
        
        total_bill = total_import_cost + total_standing_charges
        net_cost = total_bill - total_export_earnings
        
        # Calculate per day averages
        days_count = len(daily_df['date'].unique()) if not daily_df.empty else 1
        
        # Get current rates for display
        if not import_data.empty:
            latest_import = import_data.iloc[-1]
            import_rate = latest_import['rate_pence_per_kwh']
            tariff_code = latest_import['tariff_code']
        else:
            import_rate = 0
            tariff_code = ''
        
        if not export_data.empty:
            export_rate = export_data.iloc[-1]['rate_pence_per_kwh']
        else:
            export_rate = 0
        
        standing_charge = import_data.iloc[-1]['standing_charge_pence'] if not import_data.empty else 0
        
        return {
            'total_import_cost': total_import_cost,
            'total_export_earnings': total_export_earnings,
            'total_standing_charges': total_standing_charges,
            'total_bill': total_bill,
            'net_cost': net_cost,
            'total_savings': total_export_earnings,
            'avg_daily_cost': net_cost / days_count,
            'avg_daily_bill': total_bill / days_count,
            'avg_daily_savings': total_export_earnings / days_count,
            'days_count': days_count,
            'import_rate': import_rate,
            'export_rate': export_rate,
            'standing_charge_daily': standing_charge,
            'data_source': 'bill_accurate',
            'currency': 'GBP',
            'last_updated': datetime.now().isoformat(),
            'tariff_code': tariff_code
        }
    
    def add_tariff_transitions_to_figure(self, fig, start_date: str, end_date: str, 
                                       chart_type: str = 'daily') -> go.Figure:
        """Add vertical lines and annotations for tariff transitions."""
        
        if not self.bill_processor.tariff_periods:
            return fig
        
        transitions = self.bill_processor.get_tariff_transitions(start_date, end_date)
        
        for i, transition in enumerate(transitions):
            transition_date = transition['date']
            
            # Add vertical line for transition
            fig.add_vline(
                x=transition_date,
                line_dash="dash",
                line_color=self.colors['transition'],
                line_width=2,
                opacity=0.7
            )
            
            # Create annotation text
            if transition['rate_type'] == 'time_of_use':
                rate_info = transition['rate_text']
            else:
                rate_info = transition['rate_text']
            
            annotation_text = f"🔄 {transition['tariff_code']}<br>{rate_info}<br>SC: {transition['standing_charge']}p/day"
            
            if transition.get('notes'):
                annotation_text += f"<br><i>{transition['notes'][:30]}...</i>"
            
            # Position annotations alternately above/below to avoid overlap
            y_position = 0.95 if i % 2 == 0 else 0.85
            
            fig.add_annotation(
                x=transition_date,
                y=y_position,
                xref="x",
                yref="paper",
                text=annotation_text,
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=self.colors['transition'],
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor=self.colors['transition'],
                borderwidth=1,
                font=dict(size=10)
            )
        
        return fig
    
    def add_price_overlay_to_figure(self, fig, start_date: str, end_date: str, 
                                  chart_type: str = 'daily', use_rolling_avg: bool = False) -> go.Figure:
        """Add price overlay to existing consumption/cost charts."""
        
        if not self.bill_processor.tariff_periods:
            return fig
        
        # Determine frequency based on chart type
        frequency = 'H' if chart_type == 'hourly' else 'D'
        
        # Get price series
        price_df = self.bill_processor.create_price_series(start_date, end_date, frequency)
        
        if price_df.empty:
            return fig
        
        # Check if we have any Agile tariffs in the period
        has_agile = any(self.bill_processor.is_agile_tariff(code) for code in price_df['tariff_code'].unique())
        
        # Add price trace on secondary y-axis
        if chart_type == 'hourly':
            # For hourly view, show average rates by hour
            price_df['hour'] = price_df['timestamp'].dt.hour
            hourly_avg_price = price_df.groupby('hour')['rate_pence_per_kwh'].mean().reset_index()
            
            fig.add_trace(go.Scatter(
                x=hourly_avg_price['hour'],
                y=hourly_avg_price['rate_pence_per_kwh'],
                mode='lines+markers',
                name='Avg Hourly Rate',
                line=dict(color=self.colors['price_line'], width=3),
                marker=dict(size=8),
                yaxis='y2',
                hovertemplate='<b>Hour %{x}</b><br>Avg Rate: %{y:.2f}p/kWh<extra></extra>'
            ))
            
        else:
            # For daily view
            if use_rolling_avg and len(price_df) > 7:
                # Add rolling average for price
                price_df_sorted = price_df.sort_values('timestamp')
                price_df_sorted['price_rolling'] = price_df_sorted['rate_pence_per_kwh'].rolling(window=7, center=True).mean()
                
                # Show both original price (lighter) and rolling average
                fig.add_trace(go.Scatter(
                    x=price_df_sorted['timestamp'],
                    y=price_df_sorted['rate_pence_per_kwh'],
                    mode='lines',
                    name='Daily Rate',
                    line=dict(color=self.colors['price_line'], width=1, dash='dot'),
                    opacity=0.4,
                    yaxis='y2',
                    hovertemplate='<b>Daily Rate</b><br>Date: %{x}<br>Rate: %{y:.2f}p/kWh<extra></extra>'
                ))
                
                fig.add_trace(go.Scatter(
                    x=price_df_sorted['timestamp'],
                    y=price_df_sorted['price_rolling'],
                    mode='lines',
                    name='Rate (7-day avg)',
                    line=dict(color=self.colors['price_line'], width=3),
                    yaxis='y2',
                    hovertemplate='<b>Rate (7-day avg)</b><br>Date: %{x}<br>Rate: %{y:.2f}p/kWh<extra></extra>'
                ))
            else:
                # Standard price line
                price_trace_name = 'Energy Rate'
                if has_agile:
                    price_trace_name = 'Agile Rate'
                
                fig.add_trace(go.Scatter(
                    x=price_df['timestamp'],
                    y=price_df['rate_pence_per_kwh'],
                    mode='lines+markers' if len(price_df) < 50 else 'lines',
                    name=price_trace_name,
                    line=dict(color=self.colors['agile'] if has_agile else self.colors['price_line'], width=3),
                    marker=dict(size=6) if len(price_df) < 50 else None,
                    yaxis='y2',
                    hovertemplate=f'<b>{price_trace_name}</b><br>Date: %{{x}}<br>Rate: %{{y:.2f}}p/kWh<br>Tariff: %{{customdata}}<extra></extra>',
                    customdata=price_df['tariff_code']
                ))
        
        # Update layout to include secondary y-axis
        fig.update_layout(
            yaxis2=dict(
                title='Rate (p/kWh)',
                overlaying='y',
                side='right',
                showgrid=False
            )
        )
        
        return fig
    
    def create_price_comparison_chart(self, start_date: str, end_date: str) -> go.Figure:
        """Create a dedicated price comparison chart showing rate variations."""
        
        price_df = self.bill_processor.create_price_series(start_date, end_date, 'D')
        
        if price_df.empty:
            return self._create_empty_chart("No pricing data available")
        
        fig = go.Figure()
        
        # Group by tariff periods to show different colors
        tariff_codes = price_df['tariff_code'].unique()
        
        for tariff_code in tariff_codes:
            tariff_data = price_df[price_df['tariff_code'] == tariff_code].copy()
            
            # Determine color based on tariff type
            is_agile = self.bill_processor.is_agile_tariff(tariff_code)
            color = self.colors['agile'] if is_agile else self.colors['price_line']
            
            # Add trace for this tariff period
            fig.add_trace(go.Scatter(
                x=tariff_data['timestamp'],
                y=tariff_data['rate_pence_per_kwh'],
                mode='lines+markers',
                name=tariff_code,
                line=dict(color=color, width=3),
                marker=dict(size=6),
                hovertemplate=f'<b>{tariff_code}</b><br>Date: %{{x}}<br>Rate: %{{y:.2f}}p/kWh<br>Type: {tariff_data.iloc[0]["rate_type"]}<extra></extra>'
            ))
        
        # Add transitions
        transitions = self.bill_processor.get_tariff_transitions(start_date, end_date)
        for transition in transitions:
            fig.add_vline(
                x=transition['date'],
                line_dash="dash",
                line_color=self.colors['transition'],
                line_width=2,
                annotation_text=f"🔄 {transition['tariff_code']}<br>{transition['rate_text']}",
                annotation_position="top"
            )
        
        fig.update_layout(
            title='Energy Rate History & Transitions',
            xaxis_title='Date',
            yaxis_title='Rate (p/kWh)',
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def create_agile_hourly_pattern_chart(self, start_date: str, end_date: str) -> go.Figure:
        """Create hourly pattern chart for Agile tariffs showing typical daily rates."""
        
        price_df = self.bill_processor.create_price_series(start_date, end_date, 'H')
        
        if price_df.empty:
            return self._create_empty_chart("No hourly pricing data available")
        
        # Check if we have Agile data
        has_agile = any(self.bill_processor.is_agile_tariff(code) for code in price_df['tariff_code'].unique())
        
        price_df['hour'] = price_df['timestamp'].dt.hour
        price_df['weekday'] = price_df['timestamp'].dt.day_name()
        
        fig = go.Figure()
        
        if has_agile:
            # For Agile: show distribution of rates by hour
            hourly_stats = price_df.groupby('hour')['rate_pence_per_kwh'].agg(['mean', 'std', 'min', 'max']).reset_index()
            
            # Add mean line
            fig.add_trace(go.Scatter(
                x=hourly_stats['hour'],
                y=hourly_stats['mean'],
                mode='lines+markers',
                name='Average Rate',
                line=dict(color=self.colors['agile'], width=3),
                marker=dict(size=8)
            ))
            
            # Add range (min/max) as filled area
            fig.add_trace(go.Scatter(
                x=hourly_stats['hour'].tolist() + hourly_stats['hour'][::-1].tolist(),
                y=hourly_stats['max'].tolist() + hourly_stats['min'][::-1].tolist(),
                fill='toself',
                fillcolor=f'rgba({int(self.colors["agile"][1:3], 16)}, {int(self.colors["agile"][3:5], 16)}, {int(self.colors["agile"][5:7], 16)}, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='Rate Range (Min-Max)',
                hoverinfo='skip'
            ))
            
            title = 'Agile Tariff: Hourly Rate Patterns'
        else:
            # For time-of-use: show day/night pattern
            hourly_avg = price_df.groupby('hour')['rate_pence_per_kwh'].mean().reset_index()
            
            fig.add_trace(go.Scatter(
                x=hourly_avg['hour'],
                y=hourly_avg['rate_pence_per_kwh'],
                mode='lines+markers',
                name='Time-of-Use Rate',
                line=dict(color=self.colors['price_line'], width=3),
                marker=dict(size=8),
                fill='tonexty'
            ))
            
            title = 'Time-of-Use Tariff: Daily Rate Pattern'
        
        # Add peak/off-peak indicators
        fig.add_vrect(
            x0=7, x1=23,
            fillcolor="rgba(255, 200, 200, 0.2)",
            layer="below",
            line_width=0,
            annotation_text="Day Rate Period",
            annotation_position="top left"
        )
        
        fig.add_vrect(
            x0=23, x1=31,  # Wrap around midnight
            fillcolor="rgba(200, 255, 200, 0.2)",
            layer="below",
            line_width=0,
            annotation_text="Night Rate Period",
            annotation_position="top right"
        )
        
        fig.add_vrect(
            x0=-1, x1=7,
            fillcolor="rgba(200, 255, 200, 0.2)",
            layer="below",
            line_width=0
        )
        
        fig.update_layout(
            title=title,
            xaxis_title='Hour of Day',
            yaxis_title='Rate (p/kWh)',
            template='plotly_white',
            xaxis=dict(
                tickmode='linear',
                tick0=0,
                dtick=2,
                range=[-0.5, 23.5]
            )
        )
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
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
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return fig

def main():
    """Test the enhanced pricing system."""
    print("🎯 TESTING ENHANCED DASHBOARD PRICING")
    print("=" * 50)
    
    pricing_system = EnhancedDashboardPricing()
    
    if not pricing_system.bill_processor.tariff_periods:
        print("❌ No tariff configuration found")
        return
    
    # Test transitions
    transitions = pricing_system.bill_processor.get_tariff_transitions('2023-04-01', '2024-12-31')
    print(f"📅 Found {len(transitions)} tariff transitions:")
    for t in transitions:
        print(f"  {t['date']}: {t['tariff_code']} - {t['rate_text']}")
    
    # Test price series
    price_df = pricing_system.bill_processor.create_price_series('2023-04-01', '2023-05-01', 'D')
    print(f"\n💰 Price series sample ({len(price_df)} days):")
    print(price_df.head())

if __name__ == "__main__":
    main() 