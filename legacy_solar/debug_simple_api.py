import requests
import json

url = "http://localhost:5000/api/solar-chart"
payload = {"chart_type": "daily_overview", "options": []}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        
        if result.get('success'):
            chart_json = result.get('chart')
            chart_data = json.loads(chart_json)
            traces = chart_data.get('data', [])
            
            print(f"Number of traces: {len(traces)}")
            
            for i, trace in enumerate(traces):
                name = trace.get('name', 'Unknown')
                y_data = trace.get('y', [])
                x_data = trace.get('x', [])
                
                print(f"\nTrace {i}: {name}")
                print(f"Y data type: {type(y_data)}")
                print(f"X data type: {type(x_data)}")
                
                if isinstance(y_data, list) and len(y_data) > 0:
                    print(f"Y data length: {len(y_data)}")
                    print(f"First 5 Y values: {y_data[:5]}")
                    if len(y_data) > 5:
                        print(f"Last 5 Y values: {y_data[-5:]}")
                    
                    # Check for the artificial cumulative pattern
                    if len(y_data) > 10:
                        diffs = [y_data[i+1] - y_data[i] for i in range(10)]
                        print(f"First 10 differences: {[round(d, 3) for d in diffs]}")
                        
                        # Check if monotonically increasing (cumulative)
                        is_monotonic = all(y_data[i] <= y_data[i+1] for i in range(len(y_data)-1))
                        print(f"Monotonically increasing: {is_monotonic}")
                        
                        # Check average difference 
                        avg_diff = sum(diffs) / len(diffs)
                        print(f"Average difference: {avg_diff:.3f}")
                
                if isinstance(x_data, dict):
                    print(f"X data dict keys: {list(x_data.keys())}")
                    print(f"X data dict: {x_data}")
                
                # Check the full trace structure
                print(f"Trace keys: {list(trace.keys())}")
        else:
            print(f"API error: {result.get('error')}")
    else:
        print(f"HTTP error: {response.text}")

except Exception as e:
    print(f"Request error: {e}") 