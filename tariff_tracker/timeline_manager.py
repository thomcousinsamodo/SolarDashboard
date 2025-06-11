"""
Timeline manager for managing tariff periods and fetching rate data.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import os

from .models import TariffConfig, TariffPeriod, TariffTimeline, TariffType, FlowDirection, TariffRate, StandingCharge
from .api_client import OctopusAPIClient
from .logging_config import get_logger, get_structured_logger, TimingContext


class TimelineManager:
    """Manages tariff timelines and rate data fetching."""
    
    def __init__(self, config_file: str = "tariff_config.json"):
        """Initialize the timeline manager."""
        self.config_file = config_file
        self.api_client = OctopusAPIClient()
        self.logger = get_logger('timeline')
        self.structured_logger = get_structured_logger('timeline')
        
        # Load existing config or create new one
        if os.path.exists(config_file):
            self.config = TariffConfig.load_from_file(config_file)
            self.logger.info(f"Loaded existing config from {config_file}")
        else:
            self.config = TariffConfig()
            self.logger.info(f"Created new config (file will be saved to {config_file})")
        
        self.logger.info(f"TimelineManager initialized - Import periods: {len(self.config.import_timeline.periods)}, Export periods: {len(self.config.export_timeline.periods)}")
    
    def save_config(self) -> None:
        """Save the current configuration to file."""
        try:
            self.config.save_to_file(self.config_file)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def add_import_period(self, start_date: date, end_date: Optional[date], 
                         product_code: str, display_name: str, tariff_type: TariffType, 
                         region: str = "C", notes: str = "") -> TariffPeriod:
        """Add a new import tariff period."""
        tariff_code = self.api_client.build_tariff_code(product_code, region=region)
        
        period = TariffPeriod(
            start_date=start_date,
            end_date=end_date,
            product_code=product_code,
            tariff_code=tariff_code,
            display_name=display_name,
            tariff_type=tariff_type,
            flow_direction=FlowDirection.IMPORT,
            region=region,
            notes=notes
        )
        
        # Log the operation
        period_data = {
            'display_name': display_name,
            'product_code': product_code,
            'tariff_type': tariff_type.value,
            'flow_direction': FlowDirection.IMPORT.value,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            self.config.import_timeline.add_period(period)
            self.structured_logger.log_period_operation('add_import_period', period_data, success=True)
            self.logger.info(f"Added import period: {display_name} ({start_date} - {end_date or 'Ongoing'})")
            return period
        except Exception as e:
            self.structured_logger.log_period_operation('add_import_period', period_data, success=False, error=str(e))
            raise
    
    def add_export_period(self, start_date: date, end_date: Optional[date], 
                         product_code: str, display_name: str, tariff_type: TariffType, 
                         region: str = "C", notes: str = "") -> TariffPeriod:
        """Add a new export tariff period."""
        tariff_code = self.api_client.build_tariff_code(product_code, region=region, 
                                                       flow_direction="-OUTGOING")
        
        period = TariffPeriod(
            start_date=start_date,
            end_date=end_date,
            product_code=product_code,
            tariff_code=tariff_code,
            display_name=display_name,
            tariff_type=tariff_type,
            flow_direction=FlowDirection.EXPORT,
            region=region,
            notes=notes
        )
        
        self.config.export_timeline.add_period(period)
        return period
    
    def fetch_rates_for_period(self, period: TariffPeriod) -> None:
        """Fetch rate data from the API for a tariff period."""
        # Check if this is an export period - API doesn't provide export tariff data
        if period.flow_direction == FlowDirection.EXPORT:
            self.logger.warning(f"Export tariffs are not available via API - manual entry required for {period.display_name}")
            period.last_updated = datetime.now()
            
            period_data = {
                'display_name': period.display_name,
                'product_code': period.product_code,
                'tariff_type': period.tariff_type.value,
                'flow_direction': period.flow_direction.value,
                'start_date': period.start_date,
                'end_date': period.end_date
            }
            
            self.structured_logger.log_period_operation(
                'fetch_rates', period_data, success=True, rates_fetched=0, 
                error="Export tariffs not available via API"
            )
            return
        
        fetch_start = period.start_date
        fetch_end = period.end_date or date.today()
        
        # Convert to ISO format for API with BST timezone consideration
        # During BST (British Summer Time), midnight BST = 23:00 UTC previous day
        # So we need to fetch from 23:00 UTC the day before to cover BST midnight
        from datetime import timezone, timedelta
        import time
        
        # Create a timezone-aware datetime for the start date to check if BST is in effect
        start_datetime = datetime.combine(fetch_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        # Check if BST is in effect (UTC+1) by using local timezone at that date
        # Simple check: BST typically runs from last Sunday in March to last Sunday in October
        is_bst_period = (fetch_start.month > 3 and fetch_start.month < 10) or \
                       (fetch_start.month == 3 and fetch_start.day > 24) or \
                       (fetch_start.month == 10 and fetch_start.day < 25)
        
        if is_bst_period:
            # During BST, start fetching from 23:00 UTC the previous day to cover BST midnight
            api_start_datetime = start_datetime - timedelta(hours=1)
            period_from = api_start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            # During GMT, start from midnight UTC
            period_from = fetch_start.strftime('%Y-%m-%dT00:00:00Z')
        
        period_to = (fetch_end + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
        
        period_data = {
            'display_name': period.display_name,
            'product_code': period.product_code,
            'tariff_type': period.tariff_type.value,
            'flow_direction': period.flow_direction.value,
            'start_date': period.start_date,
            'end_date': period.end_date
        }
        
        self.logger.info(f"Fetching rates for {period.display_name} from {fetch_start} to {fetch_end}")
        
        with TimingContext(self.structured_logger, 'fetch_rates_for_period', {'period_name': period.display_name}):
            try:
                if period.tariff_type == TariffType.ECONOMY7:
                    self._fetch_economy7_rates(period, period_from, period_to)
                elif period.tariff_type == TariffType.AGILE:
                    self._fetch_agile_rates(period, period_from, period_to)
                else:
                    self._fetch_standard_rates(period, period_from, period_to)
                
                self._fetch_standing_charges(period, period_from, period_to)
                period.last_updated = datetime.now()
                
                rates_count = len(period.rates)
                charges_count = len(period.standing_charges)
                
                self.structured_logger.log_period_operation(
                    'fetch_rates', period_data, success=True, rates_fetched=rates_count
                )
                self.logger.info(f"Successfully fetched {rates_count} rates and {charges_count} standing charges for {period.display_name}")
                
            except Exception as e:
                error_msg = str(e)
                self.structured_logger.log_period_operation(
                    'fetch_rates', period_data, success=False, error=error_msg
                )
                self.logger.error(f"Error fetching rates for {period.display_name}: {error_msg}")
                raise
    
    def _fetch_economy7_rates(self, period: TariffPeriod, period_from: str, period_to: str) -> None:
        """Fetch Economy 7 day and night rates."""
        try:
            # Clear existing rates
            period.rates.clear()
            
            # Fetch day rates
            day_rates = self.api_client.get_tariff_rates(
                period.product_code, period.tariff_code, 
                period_from, period_to, "day-unit-rates"
            )
            
            for rate_data in day_rates:
                rate = TariffRate(
                    valid_from=datetime.fromisoformat(rate_data['valid_from'].replace('Z', '+00:00')),
                    valid_to=datetime.fromisoformat(rate_data['valid_to'].replace('Z', '+00:00')) if rate_data['valid_to'] else None,
                    value_exc_vat=rate_data['value_exc_vat'],
                    value_inc_vat=rate_data['value_inc_vat'],
                    rate_type="day"
                )
                period.rates.append(rate)
            
            # Fetch night rates
            night_rates = self.api_client.get_tariff_rates(
                period.product_code, period.tariff_code, 
                period_from, period_to, "night-unit-rates"
            )
            
            for rate_data in night_rates:
                rate = TariffRate(
                    valid_from=datetime.fromisoformat(rate_data['valid_from'].replace('Z', '+00:00')),
                    valid_to=datetime.fromisoformat(rate_data['valid_to'].replace('Z', '+00:00')) if rate_data['valid_to'] else None,
                    value_exc_vat=rate_data['value_exc_vat'],
                    value_inc_vat=rate_data['value_inc_vat'],
                    rate_type="night"
                )
                period.rates.append(rate)
                
        except Exception as e:
            print(f"Error fetching Economy 7 rates: {e}")
    
    def _fetch_agile_rates(self, period: TariffPeriod, period_from: str, period_to: str) -> None:
        """Fetch Agile half-hourly rates."""
        try:
            period.rates.clear()
            
            rates = self.api_client.get_tariff_rates(
                period.product_code, period.tariff_code, 
                period_from, period_to, "standard-unit-rates"
            )
            
            for rate_data in rates:
                rate = TariffRate(
                    valid_from=datetime.fromisoformat(rate_data['valid_from'].replace('Z', '+00:00')),
                    valid_to=datetime.fromisoformat(rate_data['valid_to'].replace('Z', '+00:00')) if rate_data['valid_to'] else None,
                    value_exc_vat=rate_data['value_exc_vat'],
                    value_inc_vat=rate_data['value_inc_vat'],
                    rate_type="standard"
                )
                period.rates.append(rate)
                
        except Exception as e:
            print(f"Error fetching Agile rates: {e}")
    
    def _fetch_standard_rates(self, period: TariffPeriod, period_from: str, period_to: str) -> None:
        """Fetch standard rates for fixed/variable tariffs."""
        try:
            period.rates.clear()
            
            rates = self.api_client.get_tariff_rates(
                period.product_code, period.tariff_code, 
                period_from, period_to, "standard-unit-rates"
            )
            
            for rate_data in rates:
                rate = TariffRate(
                    valid_from=datetime.fromisoformat(rate_data['valid_from'].replace('Z', '+00:00')),
                    valid_to=datetime.fromisoformat(rate_data['valid_to'].replace('Z', '+00:00')) if rate_data['valid_to'] else None,
                    value_exc_vat=rate_data['value_exc_vat'],
                    value_inc_vat=rate_data['value_inc_vat'],
                    rate_type="standard"
                )
                period.rates.append(rate)
                
        except Exception as e:
            print(f"Error fetching standard rates: {e}")
    
    def _fetch_standing_charges(self, period: TariffPeriod, period_from: str, period_to: str) -> None:
        """Fetch standing charges."""
        try:
            period.standing_charges.clear()
            
            charges = self.api_client.get_standing_charges(
                period.product_code, period.tariff_code, 
                period_from, period_to
            )
            
            for charge_data in charges:
                charge = StandingCharge(
                    valid_from=datetime.fromisoformat(charge_data['valid_from'].replace('Z', '+00:00')),
                    valid_to=datetime.fromisoformat(charge_data['valid_to'].replace('Z', '+00:00')) if charge_data['valid_to'] else None,
                    value_exc_vat=charge_data['value_exc_vat'],
                    value_inc_vat=charge_data['value_inc_vat']
                )
                period.standing_charges.append(charge)
                
        except Exception as e:
            print(f"Error fetching standing charges: {e}")
    
    def get_rate_at_datetime(self, dt: datetime, flow_direction: FlowDirection, 
                           rate_type: str = None) -> Optional['TariffRate']:
        """Get the rate that was active at a specific datetime.
        
        Args:
            dt: The datetime to lookup
            flow_direction: Import or export
            rate_type: Optional - if None, will be automatically determined
        """
        from datetime import timezone
        
        # Ensure dt is timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        timeline = (self.config.import_timeline if flow_direction == FlowDirection.IMPORT 
                   else self.config.export_timeline)
        
        period = timeline.get_period_at_date(dt.date())
        if not period:
            self.structured_logger.log_rate_lookup(
                dt.isoformat(), flow_direction.value, rate_type or "auto", None, None
            )
            self.logger.debug(f"No period found for {dt.date()} in {flow_direction.value} timeline")
            return None
        
        # Auto-determine rate type if not specified
        if rate_type is None:
            rate_type = self._determine_rate_type(dt, period)
        
        rate = period.get_rate_at_time(dt, rate_type)
        rate_value = rate.value_inc_vat if rate else None
        
        self.structured_logger.log_rate_lookup(
            dt.isoformat(), flow_direction.value, rate_type, rate_value, period.display_name
        )
        
        if rate:
            self.logger.debug(f"Found {rate_type} rate {rate_value}p/kWh for {dt} in period {period.display_name}")
        else:
            self.logger.debug(f"No {rate_type} rate found for {dt} in period {period.display_name}")
        
        return rate
    
    def _determine_rate_type(self, dt: datetime, period: TariffPeriod) -> str:
        """Determine the appropriate rate type based on datetime and tariff period."""
        if period.tariff_type == TariffType.ECONOMY7:
            # Economy 7: Check time to determine day/night
            # Typical Economy 7 night hours: 00:30-07:30 (but can vary by region)
            # For simplicity, using standard 00:30-07:30 UK pattern
            hour = dt.hour
            minute = dt.minute
            
            # Night rate: 00:30 to 07:30
            if (hour == 0 and minute >= 30) or (1 <= hour < 7) or (hour == 7 and minute < 30):
                return "night"
            else:
                return "day"
        else:
            # All other tariff types use standard rates
            return "standard"
    
    def get_timeline_summary(self) -> Dict:
        """Get a summary of the configured timelines."""
        import_periods = len(self.config.import_timeline.periods)
        export_periods = len(self.config.export_timeline.periods)
        
        import_active = self.config.import_timeline.get_active_period()
        export_active = self.config.export_timeline.get_active_period()
        
        return {
            'import_periods': import_periods,
            'export_periods': export_periods,
            'import_active': import_active.display_name if import_active else None,
            'export_active': export_active.display_name if export_active else None,
            'validation': self.validate_timelines()
        }
    
    def validate_timelines(self) -> Dict[str, Dict]:
        """Validate both timelines for issues."""
        import_issues = self.config.import_timeline.validate()
        export_issues = self.config.export_timeline.validate()
        
        # Log validation results
        self.structured_logger.log_validation('import', import_issues)
        self.structured_logger.log_validation('export', export_issues)
        
        return {
            'import': import_issues,
            'export': export_issues
        }
    
    def search_available_products(self, search_term: str) -> List[Dict]:
        """Search for available Octopus products."""
        return self.api_client.search_products_by_name(search_term)
    
    def refresh_all_rates(self) -> None:
        """Refresh rates for all periods in both timelines.
        
        Skips periods with manual rates (Economy 7 and export tariffs) to preserve user data.
        """
        self.logger.info("Starting refresh of all rates")
        
        # Refresh import timeline
        for period in self.config.import_timeline.periods:
            if self._should_skip_refresh(period):
                self.logger.info(f"Skipping refresh for {period.display_name} (has manual rates)")
                continue
                
            try:
                self.fetch_rates_for_period(period)
                self.logger.info(f"Refreshed rates for import period: {period.display_name}")
            except Exception as e:
                self.logger.error(f"Failed to refresh rates for import period {period.display_name}: {e}")
        
        # Refresh export timeline
        for period in self.config.export_timeline.periods:
            if self._should_skip_refresh(period):
                self.logger.info(f"Skipping refresh for {period.display_name} (has manual rates)")
                continue
                
            try:
                self.fetch_rates_for_period(period)
                self.logger.info(f"Refreshed rates for export period: {period.display_name}")
            except Exception as e:
                self.logger.error(f"Failed to refresh rates for export period {period.display_name}: {e}")
        
        self.save_config()
        self.logger.info("Completed refresh of all rates")
    
    def _should_skip_refresh(self, period: TariffPeriod) -> bool:
        """Determine if a period should be skipped during refresh to preserve manual data.
        
        Args:
            period: The tariff period to check
            
        Returns:
            True if the period should be skipped (has manual rates)
        """
        # Skip Economy 7 periods (always manual)
        if period.tariff_type == TariffType.ECONOMY7:
            return True
        
        # Skip export periods (API doesn't provide export rates)
        if period.flow_direction == FlowDirection.EXPORT:
            return True
        
        # Skip periods with product codes indicating manual entry
        if period.product_code.startswith('MANUAL-'):
            return True
        
        return False
    
    def delete_period(self, flow_direction: FlowDirection, period_index: int) -> bool:
        """Delete a period from the specified timeline."""
        timeline = (self.config.import_timeline if flow_direction == FlowDirection.IMPORT 
                   else self.config.export_timeline)
        
        if 0 <= period_index < len(timeline.periods):
            deleted_period = timeline.periods.pop(period_index)
            
            # Log the deletion
            period_data = {
                'flow_direction': flow_direction.value,
                'period_index': period_index,
                'display_name': deleted_period.display_name,
                'product_code': deleted_period.product_code
            }
            
            self.structured_logger.log_period_operation(
                'delete_period', period_data, success=True
            )
            
            self.logger.info(f"Deleted {flow_direction.value} period: {deleted_period.display_name}")
            self.save_config()
            return True
        else:
            self.logger.error(f"Invalid period index {period_index} for {flow_direction.value} timeline")
            return False
    
    def get_period_by_index(self, flow_direction: FlowDirection, period_index: int) -> Optional[TariffPeriod]:
        """Get a period by its index in the timeline."""
        timeline = (self.config.import_timeline if flow_direction == FlowDirection.IMPORT 
                   else self.config.export_timeline)
        
        if 0 <= period_index < len(timeline.periods):
            return timeline.periods[period_index]
        return None
    
    def store_manual_economy7_rates(self, period: TariffPeriod, manual_rates: Dict) -> None:
        """Store manually entered Economy 7 rates and standing charges."""
        if period.tariff_type != TariffType.ECONOMY7:
            raise ValueError("Manual Economy 7 rates can only be stored for Economy 7 periods")
        
        self._store_manual_rates(period, manual_rates, is_economy7=True)
    
    def store_manual_export_rates(self, period: TariffPeriod, manual_rates: Dict) -> None:
        """Store manually entered export rates and standing charges."""
        if period.flow_direction != FlowDirection.EXPORT:
            raise ValueError("Manual export rates can only be stored for export periods")
        
        self._store_manual_rates(period, manual_rates, is_economy7=False)
    
    def _store_manual_rates(self, period: TariffPeriod, manual_rates: Dict, is_economy7: bool = False) -> None:
        """Internal method to store manual rates (Economy 7 or export)."""
        from datetime import timezone
        
        # Clear existing rates and charges
        period.rates.clear()
        period.standing_charges.clear()
        
        # Create date range for the period (timezone-aware)
        start_datetime = datetime.combine(period.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(
            period.end_date or date.today(), 
            datetime.max.time()
        ).replace(tzinfo=timezone.utc) if period.end_date else None
        
        if is_economy7:
            # Create day and night rates for Economy 7
            day_rate = TariffRate(
                valid_from=start_datetime,
                valid_to=end_datetime,
                value_exc_vat=manual_rates['day_rate_exc_vat'],
                value_inc_vat=manual_rates['day_rate_inc_vat'],
                rate_type="day"
            )
            period.rates.append(day_rate)
            
            night_rate = TariffRate(
                valid_from=start_datetime,
                valid_to=end_datetime,
                value_exc_vat=manual_rates['night_rate_exc_vat'],
                value_inc_vat=manual_rates['night_rate_inc_vat'],
                rate_type="night"
            )
            period.rates.append(night_rate)
            
            log_msg = f"Day={manual_rates['day_rate_inc_vat']:.3f}p, Night={manual_rates['night_rate_inc_vat']:.3f}p"
        else:
            # Create single rate for export tariffs (no VAT on export sales)
            export_rate_value = manual_rates.get('export_rate_exc_vat', manual_rates.get('day_rate_exc_vat', 0))
            export_rate = TariffRate(
                valid_from=start_datetime,
                valid_to=end_datetime,
                value_exc_vat=export_rate_value,
                value_inc_vat=export_rate_value,  # Same as exc_vat since no VAT applies to exports
                rate_type="standard"
            )
            period.rates.append(export_rate)
            
            log_msg = f"Export={export_rate_value:.3f}p"
        
        # Create standing charge only for Economy 7 (not for export tariffs)
        if is_economy7:
            # Economy 7 standing charges have VAT
            standing_charge = StandingCharge(
                valid_from=start_datetime,
                valid_to=end_datetime,
                value_exc_vat=manual_rates['standing_charge_exc_vat'],
                value_inc_vat=manual_rates['standing_charge_inc_vat']
            )
            period.standing_charges.append(standing_charge)
        # Export tariffs don't have standing charges - skip this step
        
        # Update last updated timestamp
        period.last_updated = datetime.now()
        
        tariff_type = "Economy 7" if is_economy7 else "export"
        if is_economy7:
            standing_charge_log = manual_rates['standing_charge_inc_vat']
            self.logger.info(f"Stored manual {tariff_type} rates for {period.display_name}: {log_msg}, SC={standing_charge_log:.3f}p")
        else:
            # Export tariffs don't have standing charges
            self.logger.info(f"Stored manual {tariff_type} rates for {period.display_name}: {log_msg}")
