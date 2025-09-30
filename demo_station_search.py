#!/usr/bin/env python3
"""
ADDIS Station Search Demo
Author: Shardae Douglas
Date: 2025

Demonstrates the enhanced station search functionality in ADDIS
"""

import requests
import json

def demo_station_search():
    """Demonstrate the station search functionality"""
    
    print("🔍 ADDIS Station Search Demo")
    print("=" * 50)
    
    # Test the search functionality
    base_url = "http://localhost:5001"
    
    # Get available stations
    print("📡 Fetching available stations...")
    try:
        response = requests.get(f"{base_url}/api/stations")
        data = response.json()
        
        if 'stations' in data:
            stations = data['stations']
            print(f"✅ Found {len(stations)} stations")
            
            # Demo search functionality
            print("\n🔍 Search Examples:")
            
            # Search by state
            florida_stations = [s for s in stations if 'FL' in s.get('state', '')]
            print(f"   Florida stations: {len(florida_stations)}")
            
            # Search by name containing "MIAMI"
            miami_stations = [s for s in stations if 'MIAMI' in s.get('name', '').upper()]
            print(f"   Miami stations: {len(miami_stations)}")
            
            # Search by station ID pattern
            us_stations = [s for s in stations if s.get('id', '').startswith('US')]
            print(f"   US stations: {len(us_stations)}")
            
            # Show sample stations
            print(f"\n📊 Sample Stations:")
            for i, station in enumerate(stations[:5]):
                print(f"   {i+1}. {station['id']} - {station['name']} ({station.get('state', 'Unknown')})")
            
            print(f"\n💡 Search Tips:")
            print(f"   • Search by station name: 'Miami', 'New York', 'Chicago'")
            print(f"   • Search by station ID: 'USC00086700'")
            print(f"   • Search by state: 'FL', 'CA', 'NY'")
            print(f"   • Search by city: 'Miami', 'Los Angeles'")
            
            print(f"\n🚀 How to Use:")
            print(f"   1. Open ADDIS at {base_url}")
            print(f"   2. Use the search box to find stations")
            print(f"   3. Click 'Quick Select' to auto-select first match")
            print(f"   4. Click 'Run ADDIS Analysis' to analyze the station")
            
        else:
            print("❌ No stations found in response")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to ADDIS server")
        print("   Make sure the Flask app is running on http://localhost:5001")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_anomaly_analysis():
    """Demonstrate running ADDIS analysis on a searched station"""
    
    print("\n🧠 ADDIS Analysis Demo")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Example: Run analysis on a specific station
    station_id = "USC00086700"  # Oxford FL US
    start_date = "1892-01-01"
    end_date = "1892-12-31"
    confidence_threshold = 1.0
    
    print(f"📊 Running ADDIS analysis on station: {station_id}")
    print(f"📅 Date range: {start_date} to {end_date}")
    print(f"🎯 Confidence threshold: {confidence_threshold}")
    
    try:
        response = requests.post(f"{base_url}/api/anomaly-detection", 
                               json={
                                   'station_id': station_id,
                                   'start_date': start_date,
                                   'end_date': end_date,
                                   'confidence_threshold': confidence_threshold
                               })
        
        if response.status_code == 200:
            data = response.json()
            
            if 'summary' in data:
                summary = data['summary']
                print(f"✅ Analysis completed successfully!")
                print(f"   Total anomalies: {summary.get('total_anomalies', 0)}")
                print(f"   Data quality score: {summary.get('data_quality_score', 0):.1f}%")
                print(f"   Analysis period: {summary.get('analysis_period', 'N/A')}")
                
                if 'anomalies' in data and 'statistical' in data['anomalies']:
                    anomalies = data['anomalies']['statistical']['anomalies']
                    if anomalies:
                        print(f"\n🔍 Sample Anomalies:")
                        for i, anomaly in enumerate(anomalies[:3]):
                            print(f"   {i+1}. {anomaly.get('DATE', 'N/A')} - {anomaly.get('TYPE', 'N/A')} ({anomaly.get('VARIABLE', 'N/A')})")
                            print(f"      Value: {anomaly.get('VALUE', 'N/A')}°F, Z-Score: {anomaly.get('Z_SCORE', 'N/A'):.2f}")
            else:
                print(f"❌ Analysis failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to ADDIS server")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    demo_station_search()
    demo_anomaly_analysis()
