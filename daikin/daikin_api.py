#!/usr/bin/env python3
"""
Daikin Heat Pump API
Simple API to get heat pump information once authenticated
"""

import requests
import json
from datetime import datetime
from daikin_auth import DaikinAuth

class DaikinAPI:
    def __init__(self, client_id=None, client_secret=None):
        self.api_base = "https://api.onecta.daikineurope.com/v1"
        
        # Use default credentials if not provided
        if not client_id:
            client_id = "nEfgPUQTMd_eVEa0ZDYMWOxC"
        if not client_secret:
            client_secret = "6Ne0AWgG9nFwKOTs-TzDNo-gABOtzcdJSHb8yq80UR9TUfHuuX0zYy72yqmua29tHXMQVT4uHRNX8Ts4rrtaZw"
        
        self.auth = DaikinAuth(client_id, client_secret)
    
    def _get_headers(self):
        """Get authorization headers for API requests."""
        access_token = self.auth.get_access_token()
        if not access_token:
            raise Exception("Not authenticated. Run 'python daikin_auth.py' first.")
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
    
    def get_sites(self):
        """Get list of sites (properties) associated with the account."""
        try:
            headers = self._get_headers()
            response = requests.get(f"{self.api_base}/sites", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error getting sites: {e}")
    
    def get_devices(self):
        """Get list of all devices (heat pumps, etc.)."""
        try:
            headers = self._get_headers()
            response = requests.get(f"{self.api_base}/gateway-devices", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error getting devices: {e}")
    
    def get_heat_pump_data(self, device_index=0):
        """
        Get current heat pump data.
        
        Args:
            device_index (int): Index of device to get data for (default: first device)
            
        Returns:
            dict: Heat pump data including sensors, status, and consumption
        """
        try:
            devices = self.get_devices()
            
            if not devices or len(devices) <= device_index:
                raise Exception(f"No device found at index {device_index}")
            
            device = devices[device_index]
            
            # Extract basic device info
            heat_pump_data = {
                'device_id': device.get('_id'),
                'device_model': device.get('deviceModel'),
                'device_name': device.get('name', 'Heat Pump'),
                'is_online': device.get('isCloudConnectionUp', {}).get('value', False),
                'last_updated': datetime.now().isoformat(),
                'sensors': {},
                'status': {},
                'consumption': {},
                'raw_data': device  # Include raw data for debugging
            }
            
            # Extract management points (control and sensor data)
            for mp in device.get('managementPoints', []):
                mp_type = mp.get('managementPointType')
                
                if mp_type == 'climateControl':
                    # Extract temperature sensors
                    sensors = mp.get('sensoryData', {}).get('value', {})
                    for sensor_name, sensor_data in sensors.items():
                        if isinstance(sensor_data, dict) and 'value' in sensor_data:
                            heat_pump_data['sensors'][sensor_name] = {
                                'value': sensor_data['value'],
                                'unit': sensor_data.get('unit', '°C'),
                                'timestamp': sensor_data.get('timestamp')
                            }
                    
                    # Extract operating status
                    heat_pump_data['status']['on_off'] = mp.get('onOffMode', {}).get('value')
                    heat_pump_data['status']['operation_mode'] = mp.get('operationMode', {}).get('value')
                    heat_pump_data['status']['is_error'] = mp.get('isInErrorState', {}).get('value', False)
                    
                    # Extract target temperatures
                    heat_pump_data['status']['target_temp'] = mp.get('temperatureControl', {}).get('value', {}).get('operationModes', {})
                    
                    # Extract consumption data
                    consumption = mp.get('consumptionData', {}).get('value', {})
                    heat_pump_data['consumption'] = consumption
            
            return heat_pump_data
            
        except Exception as e:
            raise Exception(f"Error getting heat pump data: {e}")
    
    def get_simple_summary(self):
        """Get a simple summary of heat pump status."""
        try:
            data = self.get_heat_pump_data()
            
            summary = {
                'name': data['device_name'],
                'model': data['device_model'],
                'online': data['is_online'],
                'status': data['status'].get('on_off', 'Unknown'),
                'mode': data['status'].get('operation_mode', 'Unknown'),
                'temperatures': {}
            }
            
            # Simplified temperature readings
            for sensor, info in data['sensors'].items():
                if isinstance(info, dict):
                    summary['temperatures'][sensor] = f"{info['value']}°C"
                else:
                    summary['temperatures'][sensor] = f"{info}°C"
            
            return summary
            
        except Exception as e:
            raise Exception(f"Error getting summary: {e}")
    
    def _send_control_command(self, device_id, management_point_id, characteristic, value, path=None):
        """
        Send a control command to the heat pump.
        
        Args:
            device_id (str): Device ID from get_devices()
            management_point_id (str): Management point embedded ID
            characteristic (str): Characteristic name (e.g., 'onOffMode', 'temperatureControl')
            value: Value to set
            path (str, optional): JSON path for complex values (e.g., temperature setpoints)
        """
        try:
            headers = self._get_headers()
            headers['Content-Type'] = 'application/json'
            
            # Build request body
            request_body = {'value': value}
            if path:
                request_body['path'] = path
            
            url = f"{self.api_base}/gateway-devices/{device_id}/management-points/{management_point_id}/characteristics/{characteristic}"
            
            response = requests.patch(url, headers=headers, json=request_body, timeout=10)
            
            if response.status_code == 204:
                return True  # Success
            else:
                raise Exception(f"Control command failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error sending control command: {e}")
    
    def turn_on(self, device_index=0):
        """Turn the climate control (room heating) on."""
        devices = self.get_devices()
        if not devices or len(devices) <= device_index:
            raise Exception(f"No device found at index {device_index}")
        
        device = devices[device_index]
        device_id = device.get('_id')
        
        # Find climate control management point
        for mp in device.get('managementPoints', []):
            if mp.get('managementPointType') == 'climateControl':
                mp_id = mp.get('embeddedId')
                return self._send_control_command(device_id, mp_id, 'onOffMode', 'on')
        
        raise Exception("No climate control management point found")
    
    def turn_off(self, device_index=0):
        """Turn the climate control (room heating) off."""
        devices = self.get_devices()
        if not devices or len(devices) <= device_index:
            raise Exception(f"No device found at index {device_index}")
        
        device = devices[device_index]
        device_id = device.get('_id')
        
        # Find climate control management point
        for mp in device.get('managementPoints', []):
            if mp.get('managementPointType') == 'climateControl':
                mp_id = mp.get('embeddedId')
                return self._send_control_command(device_id, mp_id, 'onOffMode', 'off')
        
        raise Exception("No climate control management point found")
    
    def turn_hot_water_on(self, device_index=0):
        """Turn the hot water tank heating on."""
        devices = self.get_devices()
        if not devices or len(devices) <= device_index:
            raise Exception(f"No device found at index {device_index}")
        
        device = devices[device_index]
        device_id = device.get('_id')
        
        # Find domestic hot water tank management point
        for mp in device.get('managementPoints', []):
            if mp.get('managementPointType') == 'domesticHotWaterTank':
                mp_id = mp.get('embeddedId')
                return self._send_control_command(device_id, mp_id, 'onOffMode', 'on')
        
        raise Exception("No domestic hot water tank management point found")
    
    def turn_hot_water_off(self, device_index=0):
        """Turn the hot water tank heating off."""
        devices = self.get_devices()
        if not devices or len(devices) <= device_index:
            raise Exception(f"No device found at index {device_index}")
        
        device = devices[device_index]
        device_id = device.get('_id')
        
        # Find domestic hot water tank management point
        for mp in device.get('managementPoints', []):
            if mp.get('managementPointType') == 'domesticHotWaterTank':
                mp_id = mp.get('embeddedId')
                return self._send_control_command(device_id, mp_id, 'onOffMode', 'off')
        
        raise Exception("No domestic hot water tank management point found")
    
    def set_room_temperature(self, temperature, device_index=0):
        """
        Set the target room temperature for heating mode.
        
        Args:
            temperature (float): Target temperature in Celsius
            device_index (int): Device index (default: 0)
        """
        devices = self.get_devices()
        if not devices or len(devices) <= device_index:
            raise Exception(f"No device found at index {device_index}")
        
        device = devices[device_index]
        device_id = device.get('_id')
        
        # Find climate control management point
        for mp in device.get('managementPoints', []):
            if mp.get('managementPointType') == 'climateControl':
                mp_id = mp.get('embeddedId')
                # Use the path for room temperature setpoint in heating mode
                path = "/operationModes/heating/setpoints/roomTemperature"
                return self._send_control_command(device_id, mp_id, 'temperatureControl', temperature, path)
        
        raise Exception("No climate control management point found")
    
    def set_hot_water_temperature(self, temperature, device_index=0):
        """
        Set the target domestic hot water temperature.
        
        Args:
            temperature (float): Target temperature in Celsius
            device_index (int): Device index (default: 0)
        """
        devices = self.get_devices()
        if not devices or len(devices) <= device_index:
            raise Exception(f"No device found at index {device_index}")
        
        device = devices[device_index]
        device_id = device.get('_id')
        
        # Find domestic hot water tank management point
        for mp in device.get('managementPoints', []):
            if mp.get('managementPointType') == 'domesticHotWaterTank':
                mp_id = mp.get('embeddedId')
                # Use the path for hot water temperature setpoint
                path = "/operationModes/heating/setpoints/domesticHotWaterTemperature"
                return self._send_control_command(device_id, mp_id, 'temperatureControl', temperature, path)
        
        raise Exception("No domestic hot water tank management point found")
    


def main():
    """Command line interface for API testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daikin Heat Pump API')
    
    # Read-only commands
    parser.add_argument('--summary', action='store_true', help='Get simple summary')
    parser.add_argument('--full', action='store_true', help='Get full heat pump data')
    parser.add_argument('--devices', action='store_true', help='List all devices')
    parser.add_argument('--sites', action='store_true', help='List all sites')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')
    
    # Control commands
    parser.add_argument('--turn-on', action='store_true', help='Turn climate control (room heating) on')
    parser.add_argument('--turn-off', action='store_true', help='Turn climate control (room heating) off')
    parser.add_argument('--hot-water-on', action='store_true', help='Turn hot water tank heating on')
    parser.add_argument('--hot-water-off', action='store_true', help='Turn hot water tank heating off')
    parser.add_argument('--set-temp', type=float, help='Set room temperature (°C)')
    parser.add_argument('--set-hot-water', type=float, help='Set hot water temperature (°C)')
    parser.add_argument('--save-to-db', action='store_true', help='Save data to database')
    parser.add_argument('--update-db', action='store_true', help='Update database with latest data')

    
    args = parser.parse_args()
    
    try:
        api = DaikinAPI()
        
        # Check if authenticated
        if not api.auth.is_authenticated():
            print("❌ Not authenticated. Run 'python daikin_auth.py' first.")
            return
        
        if args.sites:
            print("🏠 Sites:")
            sites = api.get_sites()
            if args.json:
                print(json.dumps(sites, indent=2))
            else:
                for i, site in enumerate(sites):
                    print(f"  {i}: {site.get('name', 'Unnamed Site')}")
        
        elif args.devices:
            print("🔧 Devices:")
            devices = api.get_devices()
            if args.json:
                print(json.dumps(devices, indent=2))
            else:
                for i, device in enumerate(devices):
                    print(f"  {i}: {device.get('deviceModel', 'Unknown')} ({device.get('name', 'Unnamed')})")
        
        elif args.full:
            print("🌡️ Full Heat Pump Data:")
            data = api.get_heat_pump_data()
            if args.json:
                print(json.dumps(data, indent=2, default=str))
            else:
                print(f"Device: {data['device_name']} ({data['device_model']})")
                print(f"Online: {data['is_online']}")
                print(f"Status: {data['status']}")
                print(f"Sensors: {data['sensors']}")
                print(f"Consumption: {data['consumption']}")
        
        elif args.summary:
            print("📊 Heat Pump Summary:")
            summary = api.get_simple_summary()
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print(f"Name: {summary['name']}")
                print(f"Model: {summary['model']}")
                print(f"Online: {'✅' if summary['online'] else '❌'}")
                print(f"Status: {summary['status']}")
                print(f"Mode: {summary['mode']}")
                print("Temperatures:")
                for sensor, temp in summary['temperatures'].items():
                    print(f"  {sensor}: {temp}")
        
        elif args.turn_on:
            print("🔛 Turning climate control on...")
            api.turn_on()
            print("✅ Climate control turned on successfully!")
        
        elif args.turn_off:
            print("🔛 Turning climate control off...")
            api.turn_off()
            print("✅ Climate control turned off successfully!")
        
        elif args.hot_water_on:
            print("🚿 Turning hot water heating on...")
            api.turn_hot_water_on()
            print("✅ Hot water heating turned on successfully!")
        
        elif args.hot_water_off:
            print("🚿 Turning hot water heating off...")
            api.turn_hot_water_off()
            print("✅ Hot water heating turned off successfully!")
        
        elif args.set_temp is not None:
            print(f"🌡️ Setting room temperature to {args.set_temp}°C...")
            api.set_room_temperature(args.set_temp)
            print(f"✅ Room temperature set to {args.set_temp}°C successfully!")
        
        elif args.set_hot_water is not None:
            print(f"🚿 Setting hot water temperature to {args.set_hot_water}°C...")
            api.set_hot_water_temperature(args.set_hot_water)
            print(f"✅ Hot water temperature set to {args.set_hot_water}°C successfully!")
        
        elif args.save_to_db:
            print("💾 Saving current data to database...")
            try:
                from daikin_database import save_daikin_consumption_data, save_daikin_status_data
                heat_pump_data = api.get_heat_pump_data()
                
                consumption_saved = save_daikin_consumption_data(heat_pump_data)
                status_saved = save_daikin_status_data(heat_pump_data)
                
                if consumption_saved and status_saved:
                    print("✅ Data saved to database successfully!")
                else:
                    print("⚠️ Some data may not have been saved to database")
                    
            except Exception as e:
                print(f"❌ Error saving to database: {e}")
        
        elif args.update_db:
            print("🔄 Updating database with latest data...")
            try:
                from daikin_database import update_daikin_database
                result = update_daikin_database()
                print(f"{'✅' if result['status'] == 'success' else '⚠️' if result['status'] == 'partial' else '❌'} {result['message']}")
                if result.get('device_name'):
                    print(f"Device: {result['device_name']}")
            except Exception as e:
                print(f"❌ Error updating database: {e}")

        
        else:
            # Default: show summary
            print("📊 Heat Pump Summary:")
            summary = api.get_simple_summary()
            print(f"Name: {summary['name']}")
            print(f"Model: {summary['model']}")
            print(f"Online: {'✅' if summary['online'] else '❌'}")
            print(f"Status: {summary['status']}")
            print(f"Mode: {summary['mode']}")
            print("Temperatures:")
            for sensor, temp in summary['temperatures'].items():
                print(f"  {sensor}: {temp}")
            
            print("\n💡 Use --help to see all control options")
            print("Control commands:")
            print("  --turn-on               Turn climate control on")
            print("  --turn-off              Turn climate control off")
            print("  --hot-water-on          Turn hot water heating on")
            print("  --hot-water-off         Turn hot water heating off")
            print("  --set-temp 21           Set room temperature")
            print("  --set-hot-water 48      Set hot water temperature")
            print("  --save-to-db            Save current data to database")
            print("  --update-db             Update database with latest data")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 