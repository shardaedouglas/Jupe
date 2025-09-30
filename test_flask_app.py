#!/usr/bin/env python3
"""
Test Script for Flask Anomaly Detection App

This script tests the Flask application endpoints to ensure they work correctly.

Usage:
    python test_flask_app.py

Author: Shardae Douglas
Date: 2025
"""

import requests
import json
import time
import sys

def test_api_endpoints():
    """Test all API endpoints"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Flask Anomaly Detection API")
    print("=" * 50)
    
    # Test 1: Get stations
    print("1. Testing /api/stations endpoint...")
    try:
        response = requests.get(f"{base_url}/api/stations", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Found {len(data.get('stations', []))} stations")
        else:
            print(f"   ❌ Error: Status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Get station data
    print("2. Testing /api/station/{id}/data endpoint...")
    try:
        # Use the first station from the previous response
        stations = data.get('stations', [])
        if stations:
            station_id = stations[0]['id']
            response = requests.get(f"{base_url}/api/station/{station_id}/data", timeout=10)
            if response.status_code == 200:
                station_data = response.json()
                print(f"   ✅ Success: Found {station_data['summary']['total_records']} records for station {station_id}")
            else:
                print(f"   ❌ Error: Status code {response.status_code}")
                return False
        else:
            print("   ⚠️  No stations available for testing")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Run anomaly detection
    print("3. Testing /api/anomaly-detection endpoint...")
    try:
        # Use a small date range for testing
        test_data = {
            "station_id": station_id,
            "start_date": "2023-01-01",
            "end_date": "2023-01-31",  # Small range for quick testing
            "confidence_threshold": 0.5,
            "methods": ["statistical"]
        }
        
        response = requests.post(
            f"{base_url}/api/anomaly-detection",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            anomaly_data = response.json()
            print(f"   ✅ Success: Found {anomaly_data['summary']['total_anomalies']} anomalies")
            print(f"   📊 Data quality score: {anomaly_data['summary']['data_quality_score']}%")
        else:
            print(f"   ❌ Error: Status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n🎉 All API tests passed!")
    return True

def test_web_interface():
    """Test the web interface"""
    base_url = "http://localhost:5000"
    
    print("\n🌐 Testing Web Interface")
    print("=" * 30)
    
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            print("   ✅ Web interface is accessible")
            if "US Weather Anomaly Detection" in response.text:
                print("   ✅ Page title found")
            else:
                print("   ⚠️  Page title not found")
        else:
            print(f"   ❌ Error: Status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🚀 Starting Flask App Tests")
    print("=" * 40)
    
    # Wait a moment for the app to start
    print("⏳ Waiting for Flask app to start...")
    time.sleep(3)
    
    # Test web interface
    if not test_web_interface():
        print("\n❌ Web interface test failed")
        return False
    
    # Test API endpoints
    if not test_api_endpoints():
        print("\n❌ API tests failed")
        return False
    
    print("\n🎯 All tests completed successfully!")
    print("🌐 You can now access the web interface at: http://localhost:5000")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
