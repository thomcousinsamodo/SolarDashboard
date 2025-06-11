#!/usr/bin/env python3
"""
Database utilities for OctopusTracker.
Provides functions to interact with SQLite database instead of CSV files.
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'data/energy_data.db'

def get_db_connection():
    """Get database connection with optimizations."""
    if not os.path.exists(DATABASE_PATH):
        raise FileNotFoundError(f"Database not found at {DATABASE_PATH}. Run migrate_to_database.py first.")
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    conn.execute("PRAGMA synchronous=NORMAL")  # Better performance
    conn.execute("PRAGMA cache_size=10000")  # Better caching
    return conn

def save_consumption_data(df: pd.DataFrame, table_name: str = 'consumption_raw'):
    """Save consumption data to database."""
    try:
        conn = get_db_connection()
        
        # Ensure proper column names
        if 'meter_type' not in df.columns and 'type' in df.columns:
            df = df.rename(columns={'type': 'meter_type'})
        
        # Add timestamp if not present
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.now().isoformat()
        
        # Use REPLACE to handle duplicates
        df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
        
        conn.close()
        logger.info(f"Saved {len(df)} records to {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving consumption data: {e}")
        return False

def save_pricing_data(df: pd.DataFrame):
    """Save pricing data to database."""
    try:
        conn = get_db_connection()
        
        # Add timestamp if not present
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.now().isoformat()
        
        # Use REPLACE to handle duplicates
        df.to_sql('pricing_raw', conn, if_exists='append', index=False, method='multi')
        
        conn.close()
        logger.info(f"Saved {len(df)} pricing records")
        return True
        
    except Exception as e:
        logger.error(f"Error saving pricing data: {e}")
        return False

def load_consumption_data(start_date: Optional[str] = None, 
                         end_date: Optional[str] = None,
                         meter_type: Optional[str] = None,
                         table_name: str = 'consumption_raw') -> pd.DataFrame:
    """Load consumption data from database with optional filtering."""
    try:
        conn = get_db_connection()
        
        # Build query with filters
        query = f"SELECT * FROM {table_name}"
        params = []
        conditions = []
        
        if start_date:
            if table_name == 'consumption_raw':
                conditions.append("interval_start >= ?")
            else:
                conditions.append("date >= ?")
            params.append(start_date)
        
        if end_date:
            if table_name == 'consumption_raw':
                conditions.append("interval_start < ?")
            else:
                conditions.append("date < ?")
            params.append(end_date)
        
        if meter_type:
            conditions.append("meter_type = ?")
            params.append(meter_type)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Order by date/time
        if table_name == 'consumption_raw':
            query += " ORDER BY interval_start"
        else:
            query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        logger.info(f"Loaded {len(df)} records from {table_name}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading consumption data: {e}")
        return pd.DataFrame()

def load_pricing_data(start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     flow_direction: Optional[str] = None) -> pd.DataFrame:
    """Load pricing data from database with optional filtering."""
    try:
        conn = get_db_connection()
        
        # First check what columns exist in the pricing_raw table
        cursor = conn.execute("PRAGMA table_info(pricing_raw)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Determine the datetime column name
        datetime_col = 'datetime' if 'datetime' in columns else 'valid_from'
        
        # Build query with filters
        query = "SELECT * FROM pricing_raw"
        params = []
        conditions = []
        
        if start_date:
            conditions.append(f"{datetime_col} >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append(f"{datetime_col} < ?")
            params.append(end_date)
        
        if flow_direction:
            conditions.append("flow_direction = ?")
            params.append(flow_direction)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY {datetime_col}"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        logger.info(f"Loaded {len(df)} pricing records")
        return df
        
    except Exception as e:
        logger.error(f"Error loading pricing data: {e}")
        return pd.DataFrame()

def get_date_range() -> Dict[str, str]:
    """Get the date range of available data."""
    try:
        conn = get_db_connection()
        
        query = """
        SELECT 
            MIN(interval_start) as min_date,
            MAX(interval_start) as max_date
        FROM consumption_raw
        """
        
        cursor = conn.execute(query)
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] and result[1]:
            return {
                'start_date': result[0][:10],  # Extract date part
                'end_date': result[1][:10]
            }
        else:
            return {'start_date': None, 'end_date': None}
            
    except Exception as e:
        logger.error(f"Error getting date range: {e}")
        return {'start_date': None, 'end_date': None}

def get_data_stats() -> Dict[str, Any]:
    """Get statistics about the data in database."""
    try:
        conn = get_db_connection()
        
        stats = {}
        
        # Consumption stats
        tables = ['consumption_raw', 'consumption_daily', 'consumption_monthly']
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        # Pricing stats
        cursor = conn.execute("SELECT COUNT(*) FROM pricing_raw")
        stats['pricing_raw'] = cursor.fetchone()[0]
        
        # Date range
        date_range = get_date_range()
        stats.update(date_range)
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting data stats: {e}")
        return {}

def delete_all_consumption_data():
    """Delete all consumption data from database."""
    try:
        conn = get_db_connection()
        
        tables = ['consumption_raw', 'consumption_daily', 'consumption_monthly']
        deleted_counts = {}
        
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count_before = cursor.fetchone()[0]
            
            conn.execute(f"DELETE FROM {table}")
            deleted_counts[table] = count_before
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted data: {deleted_counts}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting consumption data: {e}")
        return False

def vacuum_database():
    """Optimize database by running VACUUM."""
    try:
        conn = get_db_connection()
        conn.execute("VACUUM")
        conn.close()
        logger.info("Database vacuumed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error vacuuming database: {e}")
        return False

def create_daily_aggregates():
    """Create daily aggregates from raw consumption data."""
    try:
        conn = get_db_connection()
        
        # Clear existing daily data
        conn.execute("DELETE FROM consumption_daily")
        
        # Create daily aggregates
        query = """
        INSERT INTO consumption_daily (date, total_kwh, meter_type, created_at)
        SELECT 
            DATE(interval_start) as date,
            SUM(consumption) as total_kwh,
            meter_type,
            CURRENT_TIMESTAMP as created_at
        FROM consumption_raw
        GROUP BY DATE(interval_start), meter_type
        ORDER BY date
        """
        
        conn.execute(query)
        conn.commit()
        
        # Get count
        cursor = conn.execute("SELECT COUNT(*) FROM consumption_daily")
        count = cursor.fetchone()[0]
        
        conn.close()
        logger.info(f"Created {count} daily aggregate records")
        return True
        
    except Exception as e:
        logger.error(f"Error creating daily aggregates: {e}")
        return False

def create_monthly_aggregates():
    """Create monthly aggregates from daily consumption data."""
    try:
        conn = get_db_connection()
        
        # Clear existing monthly data
        conn.execute("DELETE FROM consumption_monthly")
        
        # Create monthly aggregates
        query = """
        INSERT INTO consumption_monthly (year_month, total_kwh, meter_type, created_at)
        SELECT 
            substr(date, 1, 7) as year_month,
            SUM(total_kwh) as total_kwh,
            meter_type,
            CURRENT_TIMESTAMP as created_at
        FROM consumption_daily
        GROUP BY substr(date, 1, 7), meter_type
        ORDER BY year_month
        """
        
        conn.execute(query)
        conn.commit()
        
        # Get count
        cursor = conn.execute("SELECT COUNT(*) FROM consumption_monthly")
        count = cursor.fetchone()[0]
        
        conn.close()
        logger.info(f"Created {count} monthly aggregate records")
        return True
        
    except Exception as e:
        logger.error(f"Error creating monthly aggregates: {e}")
        return False

# Compatibility functions to maintain existing API
def load_consumption_daily():
    """Load daily consumption data (compatibility function)."""
    return load_consumption_data(table_name='consumption_daily')

def load_consumption_monthly():
    """Load monthly consumption data (compatibility function)."""
    return load_consumption_data(table_name='consumption_monthly')

def save_consumption_daily(df: pd.DataFrame):
    """Save daily consumption data (compatibility function)."""
    return save_consumption_data(df, table_name='consumption_daily')

def save_consumption_monthly(df: pd.DataFrame):
    """Save monthly consumption data (compatibility function)."""
    return save_consumption_data(df, table_name='consumption_monthly') 