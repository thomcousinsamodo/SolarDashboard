#!/usr/bin/env python3
"""
Daikin Heat Pump Database Management
Handles storage and retrieval of Daikin heat pump consumption data and status.
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import sys
sys.path.append('../tariff_tracker')

try:
    from logging_config import get_logger, get_structured_logger, TimingContext
    logger = get_logger('daikin.database')
    structured_logger = get_structured_logger('daikin.database')
except ImportError:
    # Fallback to basic logging if main dashboard logging not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    structured_logger = None

DATABASE_PATH = '../data/energy_data.db'

def get_db_connection():
    """Get database connection with optimizations."""
    if not os.path.exists(DATABASE_PATH):
        raise FileNotFoundError(f"Database not found at {DATABASE_PATH}. Please ensure the main dashboard database exists.")
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    conn.execute("PRAGMA synchronous=NORMAL")  # Better performance
    conn.execute("PRAGMA cache_size=10000")  # Better caching
    return conn

def create_daikin_tables():
    """Create tables for Daikin heat pump data if they don't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Table for Daikin consumption data (daily, weekly, monthly arrays)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daikin_consumption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                device_name TEXT,
                management_point_type TEXT NOT NULL,  -- 'climateControl' or 'domesticHotWaterTank'
                consumption_type TEXT NOT NULL,       -- 'electrical'
                operation_mode TEXT NOT NULL,         -- 'heating'
                period_type TEXT NOT NULL,            -- 'd', 'w', 'm' (daily, weekly, monthly)
                period_index INTEGER NOT NULL,        -- 0-23 for position in array
                consumption_kwh REAL,                 -- kWh value (null for missing data)
                recorded_at TEXT NOT NULL,            -- When this data was retrieved from API
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_id, management_point_type, consumption_type, operation_mode, period_type, period_index, recorded_at)
            )
        """)
        
        # Table for Daikin status snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daikin_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                device_name TEXT,
                device_model TEXT,
                is_online BOOLEAN,
                climate_on_off TEXT,                  -- 'on', 'off'
                climate_operation_mode TEXT,          -- 'heating'
                hot_water_on_off TEXT,               -- 'on', 'off'
                hot_water_operation_mode TEXT,       -- 'heating'
                room_temperature REAL,
                outdoor_temperature REAL,
                leaving_water_temperature REAL,
                tank_temperature REAL,
                target_room_temperature REAL,
                target_hot_water_temperature REAL,
                is_error_state BOOLEAN,
                is_warning_state BOOLEAN,
                recorded_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daikin_consumption_device_period 
            ON daikin_consumption(device_id, management_point_type, period_type, recorded_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daikin_status_device_time 
            ON daikin_status(device_id, recorded_at)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Daikin database tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating Daikin tables: {e}")
        return False

def save_daikin_consumption_data(heat_pump_data: Dict) -> bool:
    """
    Save Daikin consumption data to database.
    
    Args:
        heat_pump_data: Heat pump data from daikin_api.get_heat_pump_data()
    """
    try:
        # Ensure tables exist
        create_daikin_tables()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        device_id = heat_pump_data.get('device_id')
        device_name = heat_pump_data.get('device_name', 'Heat Pump')
        recorded_at = heat_pump_data.get('last_updated')
        consumption_data = heat_pump_data.get('consumption', {})
        
        if not device_id or not consumption_data:
            logger.warning("No device ID or consumption data found")
            return False
        
        records_saved = 0
        
        # Process consumption data for each management point
        for mp in heat_pump_data.get('raw_data', {}).get('managementPoints', []):
            mp_type = mp.get('managementPointType')
            
            if mp_type not in ['climateControl', 'domesticHotWaterTank']:
                continue
                
            mp_consumption = mp.get('consumptionData', {}).get('value', {})
            
            # Process each consumption type (electrical, gas, etc.)
            for consumption_type, type_data in mp_consumption.items():
                
                # Process each operation mode (heating, cooling, etc.)
                for operation_mode, mode_data in type_data.items():
                    
                    # Process each period type (d, w, m)
                    for period_type, period_values in mode_data.items():
                        
                        # Save each value in the array
                        for period_index, kwh_value in enumerate(period_values):
                            try:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO daikin_consumption 
                                    (device_id, device_name, management_point_type, consumption_type, 
                                     operation_mode, period_type, period_index, consumption_kwh, recorded_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    device_id, device_name, mp_type, consumption_type,
                                    operation_mode, period_type, period_index, kwh_value, recorded_at
                                ))
                                records_saved += 1
                            except Exception as e:
                                logger.warning(f"Error saving consumption record: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {records_saved} Daikin consumption records")
        return True
        
    except Exception as e:
        logger.error(f"Error saving Daikin consumption data: {e}")
        return False

def save_daikin_status_data(heat_pump_data: Dict) -> bool:
    """
    Save Daikin status snapshot to database.
    
    Args:
        heat_pump_data: Heat pump data from daikin_api.get_heat_pump_data()
    """
    try:
        # Ensure tables exist
        create_daikin_tables()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        device_id = heat_pump_data.get('device_id')
        recorded_at = heat_pump_data.get('last_updated')
        
        if not device_id:
            logger.warning("No device ID found")
            return False
        
        # Extract status information
        status = heat_pump_data.get('status', {})
        sensors = heat_pump_data.get('sensors', {})
        
        # Get temperature values
        room_temp = sensors.get('roomTemperature', {}).get('value') if isinstance(sensors.get('roomTemperature'), dict) else sensors.get('roomTemperature')
        outdoor_temp = sensors.get('outdoorTemperature', {}).get('value') if isinstance(sensors.get('outdoorTemperature'), dict) else sensors.get('outdoorTemperature')
        leaving_water_temp = sensors.get('leavingWaterTemperature', {}).get('value') if isinstance(sensors.get('leavingWaterTemperature'), dict) else sensors.get('leavingWaterTemperature')
        tank_temp = sensors.get('tankTemperature', {}).get('value') if isinstance(sensors.get('tankTemperature'), dict) else sensors.get('tankTemperature')
        
        # Get target temperatures from raw data
        climate_target = None
        hot_water_target = None
        climate_on_off = None
        hot_water_on_off = None
        climate_mode = None
        hot_water_mode = None
        
        for mp in heat_pump_data.get('raw_data', {}).get('managementPoints', []):
            mp_type = mp.get('managementPointType')
            
            if mp_type == 'climateControl':
                climate_on_off = mp.get('onOffMode', {}).get('value')
                climate_mode = mp.get('operationMode', {}).get('value')
                temp_control = mp.get('temperatureControl', {}).get('value', {})
                heating_setpoints = temp_control.get('operationModes', {}).get('heating', {}).get('setpoints', {})
                climate_target = heating_setpoints.get('roomTemperature', {}).get('value')
                
            elif mp_type == 'domesticHotWaterTank':
                hot_water_on_off = mp.get('onOffMode', {}).get('value')
                hot_water_mode = mp.get('operationMode', {}).get('value')
                temp_control = mp.get('temperatureControl', {}).get('value', {})
                heating_setpoints = temp_control.get('operationModes', {}).get('heating', {}).get('setpoints', {})
                hot_water_target = heating_setpoints.get('domesticHotWaterTemperature', {}).get('value')
        
        cursor.execute("""
            INSERT INTO daikin_status 
            (device_id, device_name, device_model, is_online, climate_on_off, climate_operation_mode,
             hot_water_on_off, hot_water_operation_mode, room_temperature, outdoor_temperature,
             leaving_water_temperature, tank_temperature, target_room_temperature, 
             target_hot_water_temperature, is_error_state, is_warning_state, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device_id,
            heat_pump_data.get('device_name'),
            heat_pump_data.get('device_model'),
            heat_pump_data.get('is_online'),
            climate_on_off,
            climate_mode,
            hot_water_on_off,
            hot_water_mode,
            room_temp,
            outdoor_temp,
            leaving_water_temp,
            tank_temp,
            climate_target,
            hot_water_target,
            status.get('is_error', False),
            False,  # is_warning_state - could extract from raw data if needed
            recorded_at
        ))
        
        conn.commit()
        conn.close()
        logger.info("Saved Daikin status snapshot")
        return True
        
    except Exception as e:
        logger.error(f"Error saving Daikin status data: {e}")
        return False

def update_daikin_database() -> Dict[str, Any]:
    """
    Fetch latest data from Daikin API and update database.
    
    Returns:
        Dict with status and statistics
    """
    start_time = datetime.now()
    
    try:
        from daikin_api import DaikinAPI
        
        # Initialize API
        api = DaikinAPI()
        
        # Check authentication
        if not api.auth.is_authenticated():
            error_msg = 'Not authenticated. Run daikin_auth.py first.'
            logger.error(f"Daikin database update failed: {error_msg}")
            return {
                'status': 'error',
                'message': error_msg
            }
        
        # Get heat pump data with timing
        if structured_logger:
            with TimingContext(structured_logger, 'daikin_api_call', {'operation': 'get_heat_pump_data'}):
                heat_pump_data = api.get_heat_pump_data()
        else:
            heat_pump_data = api.get_heat_pump_data()
        
        # Save to database with timing
        if structured_logger:
            with TimingContext(structured_logger, 'daikin_database_save', {'device_id': heat_pump_data.get('device_id')}):
                consumption_saved = save_daikin_consumption_data(heat_pump_data)
                status_saved = save_daikin_status_data(heat_pump_data)
        else:
            consumption_saved = save_daikin_consumption_data(heat_pump_data)
            status_saved = save_daikin_status_data(heat_pump_data)
        
        # Calculate duration and log success
        duration = (datetime.now() - start_time).total_seconds()
        
        if consumption_saved and status_saved:
            result = {
                'status': 'success',
                'message': 'Daikin data updated successfully',
                'device_name': heat_pump_data.get('device_name'),
                'recorded_at': heat_pump_data.get('last_updated'),
                'duration_seconds': round(duration, 2)
            }
            
            if structured_logger:
                structured_logger.log_api_call(
                    method='GET', 
                    url='daikin_onecta_api',
                    response_status=200,
                    response_time=duration
                )
                
            logger.info(f"Daikin database updated successfully in {duration:.2f}s - Device: {heat_pump_data.get('device_name')}")
            return result
        else:
            result = {
                'status': 'partial',
                'message': 'Some data may not have been saved',
                'consumption_saved': consumption_saved,
                'status_saved': status_saved,
                'duration_seconds': round(duration, 2)
            }
            logger.warning(f"Partial Daikin database update - consumption: {consumption_saved}, status: {status_saved}")
            return result
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f'Error updating database: {str(e)}'
        
        logger.error(f"Daikin database update failed after {duration:.2f}s: {e}")
        
        if structured_logger:
            structured_logger.log_api_call(
                method='GET',
                url='daikin_onecta_api', 
                error=str(e),
                response_time=duration
            )
        
        return {
            'status': 'error',
            'message': error_msg,
            'duration_seconds': round(duration, 2)
        }

def get_latest_daikin_status() -> Optional[Dict]:
    """Get the most recent Daikin status from database."""
    try:
        conn = get_db_connection()
        
        query = """
            SELECT * FROM daikin_status 
            ORDER BY recorded_at DESC 
            LIMIT 1
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
        
    except Exception as e:
        logger.error(f"Error getting latest Daikin status: {e}")
        return None

def get_daikin_consumption_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get consumption summary for the last N days.
    
    Args:
        days: Number of days to include
    """
    try:
        conn = get_db_connection()
        
        # Get daily consumption data (period_type = 'd')
        query = """
            SELECT 
                management_point_type,
                consumption_type,
                operation_mode,
                period_index,
                consumption_kwh,
                recorded_at
            FROM daikin_consumption 
            WHERE period_type = 'd' 
                AND consumption_kwh IS NOT NULL
                AND period_index < ?
            ORDER BY recorded_at DESC, period_index ASC
            LIMIT 1000
        """
        
        df = pd.read_sql_query(query, conn, params=(days,))
        conn.close()
        
        if df.empty:
            return {'status': 'no_data', 'message': 'No consumption data available'}
        
        # Calculate totals by management point
        summary = {}
        for mp_type in df['management_point_type'].unique():
            mp_data = df[df['management_point_type'] == mp_type]
            
            # Get the most recent data set
            latest_time = mp_data['recorded_at'].max()
            latest_data = mp_data[mp_data['recorded_at'] == latest_time]
            
            total_kwh = latest_data['consumption_kwh'].sum()
            valid_days = latest_data['consumption_kwh'].notna().sum()
            
            summary[mp_type] = {
                'total_kwh': round(total_kwh, 2),
                'valid_days': valid_days,
                'last_updated': latest_time
            }
        
        return {
            'status': 'success',
            'summary': summary,
            'days_requested': days
        }
        
    except Exception as e:
        logger.error(f"Error getting Daikin consumption summary: {e}")
        return {'status': 'error', 'message': str(e)}

def get_daikin_data_stats() -> Dict[str, Any]:
    """Get statistics about Daikin data in database."""
    try:
        conn = get_db_connection()
        
        stats = {}
        
        # Consumption records
        cursor = conn.execute("SELECT COUNT(*) FROM daikin_consumption")
        stats['consumption_records'] = cursor.fetchone()[0]
        
        # Status records  
        cursor = conn.execute("SELECT COUNT(*) FROM daikin_status")
        stats['status_records'] = cursor.fetchone()[0]
        
        # Date range
        cursor = conn.execute("SELECT MIN(recorded_at), MAX(recorded_at) FROM daikin_status")
        result = cursor.fetchone()
        if result and result[0]:
            stats['first_record'] = result[0]
            stats['last_record'] = result[1]
        
        # Latest status
        latest_status = get_latest_daikin_status()
        if latest_status:
            stats['latest_status'] = {
                'device_name': latest_status.get('device_name'),
                'is_online': latest_status.get('is_online'),
                'climate_status': latest_status.get('climate_on_off'),
                'hot_water_status': latest_status.get('hot_water_on_off'),
                'room_temperature': latest_status.get('room_temperature'),
                'recorded_at': latest_status.get('recorded_at')
            }
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting Daikin data stats: {e}")
        return {}

if __name__ == "__main__":
    """Command line interface for database operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daikin Database Management')
    parser.add_argument('--update', action='store_true', help='Update database with latest data')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--create-tables', action='store_true', help='Create database tables')
    parser.add_argument('--summary', type=int, default=30, help='Show consumption summary (days)')
    
    args = parser.parse_args()
    
    if args.create_tables:
        success = create_daikin_tables()
        print("✅ Tables created successfully" if success else "❌ Failed to create tables")
    
    elif args.update:
        print("🔄 Updating Daikin database...")
        result = update_daikin_database()
        print(f"{'✅' if result['status'] == 'success' else '⚠️' if result['status'] == 'partial' else '❌'} {result['message']}")
        if result.get('device_name'):
            print(f"Device: {result['device_name']}")
            print(f"Time: {result['recorded_at']}")
    
    elif args.stats:
        print("📊 Daikin Database Statistics:")
        stats = get_daikin_data_stats()
        for key, value in stats.items():
            if key == 'latest_status':
                print(f"\n🌡️ Latest Status:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")
    
    else:
        print("📈 Consumption Summary:")
        summary = get_daikin_consumption_summary(args.summary)
        if summary['status'] == 'success':
            for mp_type, data in summary['summary'].items():
                print(f"\n{mp_type}:")
                print(f"  Total: {data['total_kwh']} kWh")
                print(f"  Valid days: {data['valid_days']}")
                print(f"  Last updated: {data['last_updated']}")
        else:
            print(f"❌ {summary.get('message', 'No data')}") 