import requests
import json
from datetime import datetime, timedelta

# Test the unified dashboard API directly
url = "http://localhost:5000/api/solar-chart"

# Calculate date range for last 30 days
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

# Test different chart types with correct API format
test_requests = [
    {"chart_type": "daily_overview", "start_date": start_date, "end_date": end_date, "options": []},
    {"chart_type": "daily_overview", "start_date": start_date, "end_date": end_date, "options": ["use_rolling_avg"]},
    {"chart_type": "daily_overview", "options": []},  # No date filter - show all data
]

for i, payload in enumerate(test_requests):
    print(f"\n=== TEST {i+1}: {payload} ===")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                # Parse the chart JSON
                chart_json = result.get('chart')
                if chart_json:
                    chart_data = json.loads(chart_json)
                    traces = chart_data.get('data', [])
                    
                    print(f"Chart has {len(traces)} traces")
                    
                    for j, trace in enumerate(traces):
                        name = trace.get('name', 'Unknown')
                        y_values = trace.get('y', [])
                        
                        print(f"  Trace {j}: {name}")
                        if len(y_values) > 0:
                            print(f"    Y values (first 5): {y_values[:5]}")
                            if len(y_values) > 5:
                                print(f"    Y values (last 5): {y_values[-5:]}")
                            else:
                                print(f"    All Y values: {y_values}")
                        else:
                            print(f"    Y values: None")
                        
                        if len(y_values) > 1:
                            # Check for artificial patterns
                            diffs = [y_values[i+1] - y_values[i] for i in range(min(10, len(y_values)-1))]
                            print(f"    First 10 differences: {diffs}")
                            
                            # Check if monotonically increasing (cumulative)
                            is_monotonic = all(y_values[i] <= y_values[i+1] for i in range(len(y_values)-1))
                            print(f"    Monotonically increasing: {is_monotonic}")
                            
                            # Check if all differences are around 1
                            avg_diff = sum(diffs) / len(diffs) if diffs else 0
                            print(f"    Average difference: {avg_diff:.3f}")
                else:
                    print("No chart data in response")
            else:
                print(f"API error: {result.get('error', 'Unknown error')}")
        else:
            print(f"HTTP Error: {response.text}")
    
    except Exception as e:
        print(f"Error making request: {e}") 