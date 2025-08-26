"""
Test the weather pipeline serving endpoints.

Run this after starting the serving service.
"""

import requests
import json


def test_weather_serving():
    """Test the serving endpoints with different cities."""
    base_url = "http://localhost:8000"
    
    # Test 1: Health check
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{base_url}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    
    # Test 2: Pipeline info
    print("ℹ️ Testing info endpoint...")
    response = requests.get(f"{base_url}/info")
    print(f"Status: {response.status_code}")
    info = response.json()
    print(f"Pipeline: {info['pipeline_name']}")
    print(f"Parameters: {info['parameter_schema']}\n")
    
    # Test 3: Execute pipeline with different cities
    cities = ["Paris", "Tokyo", "New York", "Cairo"]
    
    for city in cities:
        print(f"🌍 Testing weather for {city}...")
        response = requests.post(
            f"{base_url}/invoke",
            json={"parameters": {"city": city}}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                # Handle both possible response formats
                output = result.get("results") or result.get("result")
                print(f"✅ Success! Weather analysis:")
                print(output)
                print("-" * 50)
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    
    # Test 4: Check metrics
    print("\n📊 Checking metrics...")
    response = requests.get(f"{base_url}/metrics")
    metrics = response.json()
    print(f"Total executions: {metrics['total_executions']}")
    print(f"Successful: {metrics['successful_executions']}")


if __name__ == "__main__":
    test_weather_serving()