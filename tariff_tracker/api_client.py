"""
Octopus Energy API client for fetching tariff rates and product information.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import os
import time

from .logging_config import get_logger, get_structured_logger, TimingContext


class OctopusAPIClient:
    """Client for interacting with the Octopus Energy API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the API client.
        
        Args:
            api_key: Optional API key. If not provided, will try to read from oct_api.txt
        """
        self.base_url = "https://api.octopus.energy/v1"
        self.logger = get_logger('api')
        self.structured_logger = get_structured_logger('api')
        
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_api_key()
        
        self.logger.info("OctopusAPIClient initialized")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OctopusEnergyTariffTracker/1.0'
        })
    
    def _load_api_key(self) -> str:
        """Load API key from oct_api.txt file."""
        try:
            # Look for oct_api.txt in parent directory
            api_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'oct_api.txt')
            with open(api_file, 'r') as f:
                api_key = f.readline().strip()
                self.logger.info(f"API key loaded from {api_file}")
                return api_key
        except FileNotFoundError:
            self.logger.error(f"oct_api.txt not found at expected location")
            raise FileNotFoundError("oct_api.txt not found. Please provide API key manually.")
    
    def _make_request(self, method: str, url: str, params: Dict = None) -> requests.Response:
        """Make an HTTP request with logging and error handling."""
        start_time = time.time()
        
        try:
            self.logger.debug(f"Making {method} request to {url} with params: {params}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            else:
                response = self.session.request(method, url, params=params, timeout=30)
            
            response_time = time.time() - start_time
            
            # Log the API call
            self.structured_logger.log_api_call(
                method=method,
                url=url,
                params=params,
                response_status=response.status_code,
                response_time=response_time
            )
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            # Log failed API call
            self.structured_logger.log_api_call(
                method=method,
                url=url,
                params=params,
                response_time=response_time,
                error=error_msg
            )
            
            self.logger.error(f"API request failed: {error_msg}")
            raise
    
    def get_products(self) -> Dict:
        """Get all available products from Octopus Energy."""
        with TimingContext(self.structured_logger, 'get_products'):
            response = self._make_request('GET', f"{self.base_url}/products/")
            products = response.json()
            self.logger.info(f"Retrieved {products.get('count', 0)} products from API")
            return products
    
    def get_product_details(self, product_code: str) -> Dict:
        """Get detailed information about a specific product.
        
        Args:
            product_code: The product code (e.g., 'VAR-22-11-01')
        """
        with TimingContext(self.structured_logger, 'get_product_details', {'product_code': product_code}):
            self.logger.debug(f"Fetching product details for {product_code}")
            response = self._make_request('GET', f"{self.base_url}/products/{product_code}/")
            product_data = response.json()
            self.logger.info(f"Retrieved product details for {product_code}: {product_data.get('display_name')}")
            return product_data
    
    def get_tariff_rates(self, product_code: str, tariff_code: str, 
                        period_from: str, period_to: str, 
                        rate_type: str = "standard-unit-rates") -> List[Dict]:
        """Get tariff rates for a specific period.
        
        Args:
            product_code: Product code (e.g., 'AGILE-FLEX-22-11-25')
            tariff_code: Full tariff code (e.g., 'E-1R-AGILE-FLEX-22-11-25-C')
            period_from: Start date in ISO format
            period_to: End date in ISO format
            rate_type: Type of rates to fetch ('standard-unit-rates', 'day-unit-rates', 'night-unit-rates')
        """
        details = {
            'product_code': product_code,
            'tariff_code': tariff_code,
            'rate_type': rate_type,
            'period_from': period_from,
            'period_to': period_to
        }
        
        with TimingContext(self.structured_logger, 'get_tariff_rates', details):
            url = f"{self.base_url}/products/{product_code}/electricity-tariffs/{tariff_code}/{rate_type}/"
            
            params = {
                'period_from': period_from,
                'period_to': period_to
            }
            
            self.logger.debug(f"Fetching {rate_type} for {tariff_code} from {period_from} to {period_to}")
            response = self._make_request('GET', url, params)
            rates_data = response.json()
            rates = rates_data.get('results', [])
            
            self.logger.info(f"Retrieved {len(rates)} {rate_type} for {tariff_code}")
            return rates
    
    def get_standing_charges(self, product_code: str, tariff_code: str, 
                           period_from: str, period_to: str) -> List[Dict]:
        """Get standing charges for a specific period.
        
        Args:
            product_code: Product code
            tariff_code: Full tariff code
            period_from: Start date in ISO format
            period_to: End date in ISO format
        """
        details = {
            'product_code': product_code,
            'tariff_code': tariff_code,
            'period_from': period_from,
            'period_to': period_to
        }
        
        with TimingContext(self.structured_logger, 'get_standing_charges', details):
            url = f"{self.base_url}/products/{product_code}/electricity-tariffs/{tariff_code}/standing-charges/"
            
            params = {
                'period_from': period_from,
                'period_to': period_to
            }
            
            self.logger.debug(f"Fetching standing charges for {tariff_code} from {period_from} to {period_to}")
            response = self._make_request('GET', url, params)
            charges_data = response.json()
            charges = charges_data.get('results', [])
            
            self.logger.info(f"Retrieved {len(charges)} standing charges for {tariff_code}")
            return charges
    
    def build_tariff_code(self, product_code: str, fuel_type: str = "E", 
                         payment_method: str = "1R", region: str = "C", 
                         flow_direction: str = "") -> str:
        """Build a tariff code from components.
        
        Args:
            product_code: Base product code
            fuel_type: E for electricity, G for gas
            payment_method: 1R for direct debit
            region: Region code (A-P)
            flow_direction: Empty for import, -OUTGOING for export
        
        Returns:
            Full tariff code
        """
        return f"{fuel_type}-{payment_method}-{product_code}-{region}{flow_direction}"
    
    def search_products_by_name(self, search_term: str) -> List[Dict]:
        """Search for products by name/display name.
        
        Args:
            search_term: Term to search for in product names
        """
        products = self.get_products()
        results = []
        
        search_lower = search_term.lower()
        for product in products['results']:
            if (search_lower in product['display_name'].lower() or 
                search_lower in product['code'].lower()):
                results.append(product)
        
        return results
    
    def get_agile_rates(self, region: str = "C", period_from: str = None, 
                       period_to: str = None, export: bool = False) -> List[Dict]:
        """Get Agile tariff rates for a specific region and period.
        
        Args:
            region: Region code (A-P)
            period_from: Start date in ISO format (defaults to yesterday)
            period_to: End date in ISO format (defaults to today)
            export: If True, get export rates instead of import
        """
        # Find current Agile product
        agile_products = self.search_products_by_name("agile")
        if not agile_products:
            raise ValueError("No Agile products found")
        
        # Use the most recent Agile product
        current_agile = agile_products[0]['code']
        
        # Default to last 24 hours if no period specified
        if not period_from or not period_to:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            period_from = start_date.strftime('%Y-%m-%dT00:00:00Z')
            period_to = end_date.strftime('%Y-%m-%dT00:00:00Z')
        
        flow_direction = "-OUTGOING" if export else ""
        tariff_code = self.build_tariff_code(current_agile, region=region, 
                                           flow_direction=flow_direction)
        
        return self.get_tariff_rates(current_agile, tariff_code, 
                                   period_from, period_to)
    
    def get_economy7_rates(self, product_code: str, region: str = "C", 
                          period_from: str = None, period_to: str = None) -> Dict[str, List]:
        """Get Economy 7 day and night rates.
        
        Args:
            product_code: Product code for Economy 7 tariff
            region: Region code
            period_from: Start date in ISO format
            period_to: End date in ISO format
            
        Returns:
            Dictionary with 'day' and 'night' rate lists
        """
        tariff_code = self.build_tariff_code(product_code, region=region)
        
        # Default to last 30 days if no period specified
        if not period_from or not period_to:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            period_from = start_date.strftime('%Y-%m-%dT00:00:00Z')
            period_to = end_date.strftime('%Y-%m-%dT00:00:00Z')
        
        day_rates = self.get_tariff_rates(product_code, tariff_code, 
                                        period_from, period_to, "day-unit-rates")
        night_rates = self.get_tariff_rates(product_code, tariff_code, 
                                          period_from, period_to, "night-unit-rates")
        
        return {
            'day': day_rates,
            'night': night_rates
        }
    
    def detect_tariff_type(self, product_code: str, tariff_code: str = None, region: str = "C") -> str:
        """Detect the tariff type using efficient pattern matching with selective API testing.
        
        Args:
            product_code: Product code to test
            tariff_code: Optional full tariff code, will be built if not provided
            region: Region code for building tariff code
            
        Returns:
            Detected tariff type: 'economy7', 'agile', 'go', 'fixed', or 'variable'
        """
        try:
            product_lower = product_code.lower()
            
            # Fast pattern matching for obvious cases
            if "agile" in product_lower:
                return "agile"
            elif "go" in product_lower and ("octopus-go" in product_lower or product_lower.startswith("go-")):
                return "go"
            elif "fix" in product_lower or "fixed" in product_lower:
                return "fixed"
            elif "var" in product_lower or "flexible" in product_lower:
                return "variable"
            
            # Check for specific Economy 7 patterns
            economy7_patterns = ["eco7", "economy7", "economy-7", "dual", "2-rate", "two-rate"]
            if any(pattern in product_lower for pattern in economy7_patterns):
                return "economy7"
            
            # For ambiguous cases, do selective API testing
            # Only test if we can't determine from pattern matching
            if not tariff_code:
                tariff_code = self.build_tariff_code(product_code, region=region)
            
            test_from = "2024-01-01T00:00:00Z"
            test_to = "2024-01-02T00:00:00Z"
            
            # Quick test for Economy 7 (only if pattern didn't already identify it)
            try:
                day_rates = self.get_tariff_rates(product_code, tariff_code, test_from, test_to, "day-unit-rates")
                if len(day_rates) > 0:
                    # If day rates exist, check night rates too
                    try:
                        night_rates = self.get_tariff_rates(product_code, tariff_code, test_from, test_to, "night-unit-rates")
                        if len(night_rates) > 0:
                            return "economy7"
                    except:
                        pass
            except:
                pass
            
            # Default to variable for most modern tariffs
            return "variable"
                    
        except Exception as e:
            self.logger.warning(f"Could not detect tariff type for {product_code}: {e}")
            # Fallback to pattern matching only
            product_lower = product_code.lower()
            if "agile" in product_lower:
                return "agile"
            elif "go" in product_lower:
                return "go"
            elif "fix" in product_lower:
                return "fixed"
            else:
                return "variable" 