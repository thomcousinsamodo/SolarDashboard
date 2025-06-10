#!/usr/bin/env python3
"""
Simple example to test Octopus Energy API public endpoints
This script demonstrates fetching public data without authentication
"""

import requests
import json
from datetime import datetime, timedelta


def test_public_endpoints():
    """Test public API endpoints that don't require authentication"""
    
    base_url = "https://api.octopus.energy/v1"
    
    print("Testing Octopus Energy API Public Endpoints")
    print("=" * 50)
    
    # 1. Get all products
    print("\n1. Fetching available products...")
    try:
        response = requests.get(f"{base_url}/products/")
        response.raise_for_status()
        products = response.json()
        
        print(f"Found {products['count']} products")
        print("\nFirst 5 products:")
        for product in products['results'][:5]:
            print(f"  - {product['display_name']} ({product['code']})")
            print(f"    Type: {'Variable' if product['is_variable'] else 'Fixed'}")
            print(f"    Green: {product['is_green']}")
            print()
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching products: {e}")
    
    # 2. Get Agile prices (example)
    print("\n2. Fetching Agile tariff prices...")
    try:
        # Get recent Agile prices for region C
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        period_from = start_date.strftime('%Y-%m-%dT00:00:00Z')
        period_to = end_date.strftime('%Y-%m-%dT00:00:00Z')
        
        # Find current Agile product (this may need to be updated with current product code)
        agile_url = f"{base_url}/products/AGILE-FLEX-22-11-25/electricity-tariffs/E-1R-AGILE-FLEX-22-11-25-C/standard-unit-rates/"
        
        params = {
            'period_from': period_from,
            'period_to': period_to
        }
        
        response = requests.get(agile_url, params=params)
        
        if response.status_code == 200:
            prices = response.json()
            print(f"Found {prices['count']} price periods")
            
            if prices['results']:
                print("\nSample prices (pence/kWh inc VAT):")
                for price in prices['results'][:5]:
                    valid_from = datetime.fromisoformat(price['valid_from'].replace('Z', '+00:00'))
                    print(f"  {valid_from.strftime('%Y-%m-%d %H:%M')}: {price['value_inc_vat']:.2f}p")
        else:
            print(f"Could not fetch Agile prices (status: {response.status_code})")
            print("This might be because the product code has changed.")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Agile prices: {e}")
    
    # 3. Get product details
    print("\n3. Fetching product details...")
    try:
        # Get details for a specific product
        response = requests.get(f"{base_url}/products/VAR-22-11-01/")
        
        if response.status_code == 200:
            product = response.json()
            print(f"Product: {product['display_name']}")
            print(f"Description: {product['description'][:100]}...")
            print(f"Available from: {product['available_from']}")
            print(f"Variable: {product['is_variable']}")
            print(f"Green: {product['is_green']}")
            
            # Show available tariffs
            if 'single_register_electricity_tariffs' in product:
                print("\nAvailable regions:")
                for region, tariff in product['single_register_electricity_tariffs'].items():
                    if 'direct_debit_monthly' in tariff:
                        standing_charge = tariff['direct_debit_monthly']['standing_charge_inc_vat']
                        unit_rate = tariff['direct_debit_monthly'].get('standard_unit_rate_inc_vat', 'N/A')
                        print(f"  Region {region.replace('_', '')}: Standing charge {standing_charge}p/day, Unit rate {unit_rate}p/kWh")
        else:
            print(f"Could not fetch product details (status: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching product details: {e}")


if __name__ == "__main__":
    test_public_endpoints() 