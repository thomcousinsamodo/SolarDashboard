#!/usr/bin/env python3
"""
Price Configuration and Calculations for Solar Dashboard
Handles energy tariffs, standing charges, and cost calculations
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Optional

# Default UK Energy Tariffs (pence per kWh)
DEFAULT_TARIFFS = {
    'import_rate': 28.62,  # Standard variable tariff (Oct 2024)
    'export_rate': 15.0,   # SEG export rate (typical range 4-15p)
    'standing_charge_daily': 60.10,  # Daily standing charge (pence)
    'currency': 'GBP',
    'unit': 'pence'
}

def get_real_pricing_config():
    """Get real pricing configuration from Octopus Energy API"""
    try:
        from octopus_pricing_api import OctopusPricingAPI
        
        print("🔍 Fetching real pricing data from Octopus Energy API...")
        api = OctopusPricingAPI()
        config = api.create_pricing_config()
        
        # Validate the config has required fields
        required_fields = ['import_rate', 'export_rate', 'standing_charge_daily']
        for field in required_fields:
            if field not in config or config[field] is None:
                print(f"⚠️  Missing {field}, using default value")
                config[field] = DEFAULT_TARIFFS[field]
        
        return config
        
    except ImportError:
        print("⚠️  Octopus pricing API not available, using default tariffs")
        return DEFAULT_TARIFFS.copy()
    except Exception as e:
        print(f"⚠️  Error fetching real pricing: {e}")
        print("📊 Falling back to default tariffs")
        return DEFAULT_TARIFFS.copy()

class PriceCalculator:
    """Calculate energy costs and savings"""
    
    def __init__(self, tariff_config: Dict = None):
        """Initialize with tariff configuration"""
        self.config = tariff_config or DEFAULT_TARIFFS.copy()
        
    def calculate_daily_costs(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate daily costs and savings"""
        if daily_df.empty:
            return daily_df
            
        df = daily_df.copy()
        
        # Separate import and export data
        import_data = df[df['meter_type'] == 'import'].copy()
        export_data = df[df['meter_type'] == 'export'].copy()
        
        # Calculate costs for imports (pence)
        if not import_data.empty:
            import_data['cost_pence'] = import_data['total_kwh'] * self.config['import_rate']
            import_data['cost_pounds'] = import_data['cost_pence'] / 100
            
        # Calculate earnings for exports (pence)
        if not export_data.empty:
            export_data['cost_pence'] = export_data['total_kwh'] * self.config['export_rate']
            export_data['cost_pounds'] = export_data['cost_pence'] / 100
            
        # Combine back together
        result_df = pd.concat([import_data, export_data], ignore_index=True)
        
        # Add standing charges to import days only
        result_df['standing_charge_pence'] = 0.0
        result_df['standing_charge_pounds'] = 0.0
        
        if not import_data.empty:
            import_mask = result_df['meter_type'] == 'import'
            result_df.loc[import_mask, 'standing_charge_pence'] = float(self.config['standing_charge_daily'])
            result_df.loc[import_mask, 'standing_charge_pounds'] = float(self.config['standing_charge_daily']) / 100
            
        # Calculate total daily cost (import cost + standing charge)
        result_df['total_cost_pence'] = result_df['cost_pence'] + result_df['standing_charge_pence']
        result_df['total_cost_pounds'] = result_df['total_cost_pence'] / 100
        
        return result_df.sort_values('date').reset_index(drop=True)
    
    def get_summary_stats(self, daily_df: pd.DataFrame) -> Dict:
        """Calculate summary financial statistics"""
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
            'import_rate': self.config['import_rate'],
            'export_rate': self.config['export_rate'],
            'standing_charge': self.config['standing_charge_daily']
        }

def format_currency(value: float, currency: str = 'GBP', show_pence: bool = False) -> str:
    """Format currency values for display"""
    if currency == 'GBP':
        if show_pence and abs(value) < 1.0:
            return f"{value * 100:.1f}p"
        else:
            return f"£{value:.2f}"
    else:
        return f"{value:.2f} {currency}"
