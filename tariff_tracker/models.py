"""
Data models for tariff tracking and timeline management.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Union
import json
from enum import Enum


class TariffType(Enum):
    """Types of tariffs supported."""
    FIXED = "fixed"
    VARIABLE = "variable"
    AGILE = "agile"
    ECONOMY7 = "economy7"
    GO = "go"


class FlowDirection(Enum):
    """Direction of energy flow."""
    IMPORT = "import"
    EXPORT = "export"


@dataclass
class TariffRate:
    """Represents a tariff rate for a specific time period."""
    valid_from: datetime
    valid_to: Optional[datetime]
    value_exc_vat: float
    value_inc_vat: float
    rate_type: str = "standard"  # standard, day, night
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'value_exc_vat': self.value_exc_vat,
            'value_inc_vat': self.value_inc_vat,
            'rate_type': self.rate_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TariffRate':
        """Create from dictionary."""
        return cls(
            valid_from=datetime.fromisoformat(data['valid_from']),
            valid_to=datetime.fromisoformat(data['valid_to']) if data['valid_to'] else None,
            value_exc_vat=data['value_exc_vat'],
            value_inc_vat=data['value_inc_vat'],
            rate_type=data.get('rate_type', 'standard')
        )


@dataclass
class StandingCharge:
    """Represents a standing charge for a specific time period."""
    valid_from: datetime
    valid_to: Optional[datetime]
    value_exc_vat: float
    value_inc_vat: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'value_exc_vat': self.value_exc_vat,
            'value_inc_vat': self.value_inc_vat
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StandingCharge':
        """Create from dictionary."""
        return cls(
            valid_from=datetime.fromisoformat(data['valid_from']),
            valid_to=datetime.fromisoformat(data['valid_to']) if data['valid_to'] else None,
            value_exc_vat=data['value_exc_vat'],
            value_inc_vat=data['value_inc_vat']
        )


@dataclass
class TariffPeriod:
    """Represents a period when a user was on a specific tariff."""
    
    # Basic information
    start_date: date
    end_date: Optional[date]
    product_code: str
    tariff_code: str
    display_name: str
    tariff_type: TariffType
    flow_direction: FlowDirection
    region: str
    
    # Rate data (fetched from API)
    rates: List[TariffRate] = field(default_factory=list)
    standing_charges: List[StandingCharge] = field(default_factory=list)
    
    # Additional metadata
    notes: str = ""
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Set last_updated if not provided."""
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    @property
    def is_active(self) -> bool:
        """Check if this tariff period is currently active."""
        today = date.today()
        return self.start_date <= today and (self.end_date is None or self.end_date >= today)
    
    @property
    def duration_days(self) -> Optional[int]:
        """Get the duration of this tariff period in days."""
        if self.end_date is None:
            return None
        return (self.end_date - self.start_date).days + 1
    
    def get_rate_at_time(self, dt: datetime, rate_type: str = "standard") -> Optional[TariffRate]:
        """Get the rate that was valid at a specific datetime."""
        from datetime import timezone
        
        # Convert dt to timezone-aware if it's naive (assume UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        for rate in self.rates:
            if (rate.valid_from <= dt and 
                rate.rate_type == rate_type and
                (rate.valid_to is None or rate.valid_to > dt)):
                return rate
        return None
    
    def get_standing_charge_at_time(self, dt: datetime) -> Optional[StandingCharge]:
        """Get the standing charge that was valid at a specific datetime."""
        from datetime import timezone
        
        # Convert dt to timezone-aware if it's naive (assume UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        for charge in self.standing_charges:
            if (charge.valid_from <= dt and 
                (charge.valid_to is None or charge.valid_to > dt)):
                return charge
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'product_code': self.product_code,
            'tariff_code': self.tariff_code,
            'display_name': self.display_name,
            'tariff_type': self.tariff_type.value,
            'flow_direction': self.flow_direction.value,
            'region': self.region,
            'rates': [rate.to_dict() for rate in self.rates],
            'standing_charges': [charge.to_dict() for charge in self.standing_charges],
            'notes': self.notes,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TariffPeriod':
        """Create from dictionary."""
        return cls(
            start_date=date.fromisoformat(data['start_date']),
            end_date=date.fromisoformat(data['end_date']) if data['end_date'] else None,
            product_code=data['product_code'],
            tariff_code=data['tariff_code'],
            display_name=data['display_name'],
            tariff_type=TariffType(data['tariff_type']),
            flow_direction=FlowDirection(data['flow_direction']),
            region=data['region'],
            rates=[TariffRate.from_dict(rate) for rate in data['rates']],
            standing_charges=[StandingCharge.from_dict(charge) for charge in data['standing_charges']],
            notes=data.get('notes', ''),
            last_updated=datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else None
        )


@dataclass
class TariffTimeline:
    """Represents a timeline of tariff periods for import or export."""
    
    flow_direction: FlowDirection
    periods: List[TariffPeriod] = field(default_factory=list)
    
    def add_period(self, period: TariffPeriod) -> None:
        """Add a tariff period to the timeline."""
        if period.flow_direction != self.flow_direction:
            raise ValueError(f"Period flow direction {period.flow_direction} doesn't match timeline {self.flow_direction}")
        
        self.periods.append(period)
        self._sort_periods()
    
    def remove_period(self, index: int) -> None:
        """Remove a tariff period by index."""
        if 0 <= index < len(self.periods):
            self.periods.pop(index)
    
    def _sort_periods(self) -> None:
        """Sort periods by start date."""
        self.periods.sort(key=lambda p: p.start_date)
    
    def get_period_at_date(self, target_date: date) -> Optional[TariffPeriod]:
        """Get the tariff period that was active on a specific date."""
        for period in self.periods:
            if (period.start_date <= target_date and 
                (period.end_date is None or period.end_date >= target_date)):
                return period
        return None
    
    def get_active_period(self) -> Optional[TariffPeriod]:
        """Get the currently active tariff period."""
        return self.get_period_at_date(date.today())
    
    def get_gaps(self) -> List[tuple]:
        """Find gaps in the timeline where no tariff is defined."""
        gaps = []
        sorted_periods = sorted(self.periods, key=lambda p: p.start_date)
        
        for i in range(len(sorted_periods) - 1):
            current_end = sorted_periods[i].end_date
            next_start = sorted_periods[i + 1].start_date
            
            if current_end and current_end + timedelta(days=1) < next_start:
                gaps.append((current_end + timedelta(days=1), next_start - timedelta(days=1)))
        
        return gaps
    
    def get_overlaps(self) -> List[tuple]:
        """Find overlapping periods in the timeline."""
        overlaps = []
        sorted_periods = sorted(self.periods, key=lambda p: p.start_date)
        
        for i in range(len(sorted_periods) - 1):
            current = sorted_periods[i]
            next_period = sorted_periods[i + 1]
            
            current_end = current.end_date or date.max
            if current_end >= next_period.start_date:
                overlaps.append((i, i + 1))
        
        return overlaps
    
    def validate(self) -> Dict[str, List]:
        """Validate the timeline and return any issues found."""
        issues = {
            'gaps': self.get_gaps(),
            'overlaps': self.get_overlaps(),
            'invalid_periods': []
        }
        
        for i, period in enumerate(self.periods):
            if period.end_date and period.end_date < period.start_date:
                issues['invalid_periods'].append((i, "End date before start date"))
        
        return issues
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'flow_direction': self.flow_direction.value,
            'periods': [period.to_dict() for period in self.periods]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TariffTimeline':
        """Create from dictionary."""
        timeline = cls(flow_direction=FlowDirection(data['flow_direction']))
        timeline.periods = [TariffPeriod.from_dict(period) for period in data['periods']]
        return timeline


@dataclass
class TariffConfig:
    """Complete configuration containing both import and export timelines."""
    
    import_timeline: TariffTimeline = field(default_factory=lambda: TariffTimeline(FlowDirection.IMPORT))
    export_timeline: TariffTimeline = field(default_factory=lambda: TariffTimeline(FlowDirection.EXPORT))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'import_timeline': self.import_timeline.to_dict(),
            'export_timeline': self.export_timeline.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TariffConfig':
        """Create from dictionary."""
        return cls(
            import_timeline=TariffTimeline.from_dict(data['import_timeline']),
            export_timeline=TariffTimeline.from_dict(data['export_timeline'])
        )
    
    def save_to_file(self, filename: str) -> None:
        """Save configuration to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'TariffConfig':
        """Load configuration from JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data) 