"""
Logging configuration for the Octopus Tariff Tracker.
"""

import logging
import logging.handlers
import os
from datetime import datetime, date
from typing import Dict, Any
import json
import sys


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """Set up comprehensive logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Helper function to create safe rotating handler
    def create_safe_handler(filename, max_bytes=10*1024*1024, backup_count=5):
        """Create a rotating file handler that's safer on Windows."""
        try:
            # Use TimedRotatingFileHandler instead for better Windows compatibility
            handler = logging.handlers.TimedRotatingFileHandler(
                filename, when='midnight', interval=1, backupCount=backup_count,
                encoding='utf-8', delay=True
            )
            # Set size-based rotation as well if needed
            handler.maxBytes = max_bytes
            return handler
        except Exception:
            # Fallback to basic file handler if rotation fails
            return logging.FileHandler(filename, encoding='utf-8', delay=True)
    
    # Main application log
    app_log_file = os.path.join(log_dir, 'tariff_tracker.log')
    app_handler = create_safe_handler(app_log_file)
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)
    
    # API-specific log
    api_log_file = os.path.join(log_dir, 'api_calls.log')
    api_handler = create_safe_handler(api_log_file, max_bytes=5*1024*1024, backup_count=3)
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(detailed_formatter)
    
    # Set up API logger
    api_logger = logging.getLogger('tariff_tracker.api')
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.DEBUG)
    
    # Timeline operations log
    timeline_log_file = os.path.join(log_dir, 'timeline_operations.log')
    timeline_handler = create_safe_handler(timeline_log_file, max_bytes=5*1024*1024, backup_count=3)
    timeline_handler.setLevel(logging.DEBUG)
    timeline_handler.setFormatter(detailed_formatter)
    
    # Set up timeline logger
    timeline_logger = logging.getLogger('tariff_tracker.timeline')
    timeline_logger.addHandler(timeline_handler)
    timeline_logger.setLevel(logging.DEBUG)
    
    # Error-only log for critical issues
    error_log_file = os.path.join(log_dir, 'errors.log')
    error_handler = create_safe_handler(error_log_file, max_bytes=5*1024*1024, backup_count=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Performance log for timing operations
    perf_log_file = os.path.join(log_dir, 'performance.log')
    perf_handler = create_safe_handler(perf_log_file, max_bytes=5*1024*1024, backup_count=3)
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(detailed_formatter)
    
    # Set up performance logger
    perf_logger = logging.getLogger('tariff_tracker.performance')
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    
    logging.info(f"Logging initialized - Level: {log_level}, Directory: {log_dir}")


class StructuredLogger:
    """Helper class for structured logging with additional context."""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
    
    def log_api_call(self, method: str, url: str, params: Dict = None, 
                     response_status: int = None, response_time: float = None,
                     error: str = None) -> None:
        """Log API call details."""
        log_data = {
            'type': 'api_call',
            'method': method,
            'url': url,
            'params': params or {},
            'response_status': response_status,
            'response_time_ms': response_time * 1000 if response_time else None,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            self.logger.error(f"API call failed: {json.dumps(log_data)}")
        else:
            self.logger.info(f"API call: {json.dumps(log_data)}")
    
    def log_period_operation(self, operation: str, period_data: Dict, 
                           success: bool = True, error: str = None,
                           rates_fetched: int = None) -> None:
        """Log tariff period operations."""
        log_data = {
            'type': 'period_operation',
            'operation': operation,
            'period': {
                'display_name': period_data.get('display_name'),
                'product_code': period_data.get('product_code'),
                'tariff_type': period_data.get('tariff_type'),
                'flow_direction': period_data.get('flow_direction'),
                'start_date': str(period_data.get('start_date')),
                'end_date': str(period_data.get('end_date')) if period_data.get('end_date') else None
            },
            'success': success,
            'error': error,
            'rates_fetched': rates_fetched,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            self.logger.error(f"Period operation failed: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Period operation: {json.dumps(log_data)}")
    
    def log_rate_lookup(self, datetime_str: str, flow_direction: str, 
                       rate_type: str, found_rate: float = None,
                       period_name: str = None) -> None:
        """Log rate lookup operations."""
        log_data = {
            'type': 'rate_lookup',
            'datetime': datetime_str,
            'flow_direction': flow_direction,
            'rate_type': rate_type,
            'found_rate': found_rate,
            'period_name': period_name,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Rate lookup: {json.dumps(log_data)}")
    
    def log_performance(self, operation: str, duration: float, 
                       details: Dict = None) -> None:
        """Log performance metrics."""
        perf_logger = logging.getLogger('tariff_tracker.performance')
        
        log_data = {
            'type': 'performance',
            'operation': operation,
            'duration_ms': duration * 1000,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        
        perf_logger.info(f"Performance: {json.dumps(log_data)}")
    
    def log_validation(self, timeline_type: str, issues: Dict) -> None:
        """Log timeline validation results."""
        # Convert date objects to strings for JSON serialization
        serializable_issues = self._convert_dates_to_strings(issues)
        
        log_data = {
            'type': 'validation',
            'timeline_type': timeline_type,
            'issues': serializable_issues,
            'has_issues': any(issues.values()),
            'timestamp': datetime.now().isoformat()
        }
        
        if any(issues.values()):
            self.logger.warning(f"Timeline validation issues: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Timeline validation passed: {json.dumps(log_data)}")
    
    def _convert_dates_to_strings(self, obj):
        """Recursively convert date and datetime objects to strings for JSON serialization."""
        if isinstance(obj, dict):
            return {key: self._convert_dates_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_dates_to_strings(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        else:
            return obj


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, logger: StructuredLogger, operation: str, details: Dict = None):
        self.logger = logger
        self.operation = operation
        self.details = details or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            if exc_type:
                self.details['error'] = str(exc_val)
            self.logger.log_performance(self.operation, duration, self.details)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f'tariff_tracker.{name}')


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(f'tariff_tracker.{name}')


# Initialize logging when module is imported (only if not already done)
import logging as _logging
if not _logging.getLogger().handlers:
    setup_logging() 