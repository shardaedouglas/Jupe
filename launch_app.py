#!/usr/bin/env python3
"""
ADDIS - AI-Powered Data Discrepancy Identification System
Flask App Launcher

This script launches the Flask web interface for ADDIS discrepancy detection.

Usage:
    python launch_app.py

Author: Shardae Douglas
Date: 2025
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'flask', 'pandas', 'numpy', 'matplotlib', 
        'seaborn', 'scikit-learn', 'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install missing packages with:")
        print("   pip install -r requirements_flask.txt")
        return False
    
    return True

def check_data_files():
    """Check if required data files exist"""
    required_files = [
        'us_stations.csv',
        'us_enhanced_weather_data.csv'
    ]
    
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required data files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n📊 Generate data files with:")
        print("   python run_us_filter.py")
        return False
    
    return True

def check_anomaly_detector():
    """Check if anomaly detector module exists"""
    if not os.path.exists('enhanced_weather_anomaly_detector.py'):
        print("❌ Missing anomaly detector module:")
        print("   - enhanced_weather_anomaly_detector.py")
        print("\n🔧 This module should be created as part of the anomaly detection system")
        return False
    
    return True

def main():
    """Main launcher function"""
    print("🚀 ADDIS - AI-Powered Data Discrepancy Identification System Launcher")
    print("=" * 70)
    
    # Check requirements
    print("🔍 Checking requirements...")
    if not check_requirements():
        return False
    
    print("✅ All required packages are installed")
    
    # Check data files
    print("\n📊 Checking data files...")
    if not check_data_files():
        return False
    
    print("✅ All required data files are available")
    
    # Check anomaly detector
    print("\n🔧 Checking anomaly detector...")
    if not check_anomaly_detector():
        return False
    
    print("✅ Anomaly detector module is available")
    
    # Launch the Flask app
    print("\n🌐 Launching ADDIS Flask web interface...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 70)
    
    try:
        # Import and run the Flask app
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error launching Flask app: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
