#!/usr/bin/env python3
"""
ADDIS - AI-Powered Data Discrepancy Identification System
Flask Web Interface for Weather Data Discrepancy Detection

A web application that allows users to run discrepancy detection for specific US stations
with date ranges and generates comprehensive anomaly reports.

Author: Shardae Douglas
Date: 2025
"""

from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

# Import our anomaly detection modules
import sys
sys.path.append('.')
from enhanced_weather_anomaly_detector import EnhancedWeatherAnomalyDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Global variables for caching
detector = None
us_stations_data = None
us_weather_data = None

def load_data():
    """Load US stations and weather data"""
    global us_stations_data, us_weather_data
    
    try:
        # Load US stations metadata
        if os.path.exists('us_stations.csv'):
            us_stations_data = pd.read_csv('us_stations.csv')
            logger.info(f"Loaded {len(us_stations_data)} US stations")
        else:
            logger.warning("US stations data not found. Run us_station_filter.py first.")
            us_stations_data = pd.DataFrame()
        
        # Load US weather data
        if os.path.exists('us_enhanced_weather_data.csv'):
            us_weather_data = pd.read_csv('us_enhanced_weather_data.csv')
            logger.info(f"Loaded {len(us_weather_data)} weather records")
        else:
            logger.warning("US weather data not found. Run us_station_filter.py first.")
            us_weather_data = pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        us_stations_data = pd.DataFrame()
        us_weather_data = pd.DataFrame()

def initialize_detector():
    """Initialize the anomaly detector"""
    global detector
    
    try:
        detector = EnhancedWeatherAnomalyDetector()
        logger.info("Anomaly detector initialized")
    except Exception as e:
        logger.error(f"Error initializing detector: {e}")
        detector = None

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/stations')
def get_stations():
    """Get list of available US stations"""
    global us_stations_data
    
    if us_stations_data.empty:
        return jsonify({'error': 'No station data available'})
    
    # Get stations with weather data
    if not us_weather_data.empty:
        available_stations = us_weather_data['STATION'].unique()
        stations_info = us_stations_data[us_stations_data['STATION_ID'].isin(available_stations)]
    else:
        stations_info = us_stations_data
    
    # Format station data for frontend
    stations = []
    for _, station in stations_info.iterrows():
        stations.append({
            'id': station['STATION_ID'],
            'name': station['STATION_NAME'],
            'state': station.get('STATE', 'Unknown'),
            'latitude': station['LATITUDE'],
            'longitude': station['LONGITUDE'],
            'elevation': station['ELEVATION']
        })
    
    return jsonify({'stations': stations})

@app.route('/api/station/<station_id>/data')
def get_station_data(station_id):
    """Get weather data for a specific station"""
    global us_weather_data
    
    if us_weather_data.empty:
        return jsonify({'error': 'No weather data available'})
    
    # Filter data for the specific station
    station_data = us_weather_data[us_weather_data['STATION'] == station_id].copy()
    
    if station_data.empty:
        return jsonify({'error': f'No data found for station {station_id}'})
    
    # Convert to date range
    station_data['DATE'] = pd.to_datetime(station_data['DATE'])
    date_range = {
        'start': station_data['DATE'].min().strftime('%Y-%m-%d'),
        'end': station_data['DATE'].max().strftime('%Y-%m-%d')
    }
    
    # Get data summary
    summary = {
        'total_records': len(station_data),
        'date_range': date_range,
        'temperature_records': station_data['TMAX'].notna().sum(),
        'precipitation_records': station_data['PRCP'].notna().sum(),
        'has_metadata': 'LATITUDE' in station_data.columns
    }
    
    return jsonify({
        'station_id': station_id,
        'summary': summary,
        'data': station_data.to_dict('records')
    })

@app.route('/api/anomaly-detection', methods=['POST'])
def run_anomaly_detection():
    """Run anomaly detection for a specific station and date range"""
    global detector, us_weather_data
    
    try:
        data = request.get_json()
        station_id = data.get('station_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        methods = data.get('methods', ['statistical', 'ml'])
        confidence_threshold = data.get('confidence_threshold', 0.5)
        
        logger.info(f"Running anomaly detection for station {station_id} from {start_date} to {end_date}")
        
        # Validate inputs
        if not station_id or not start_date or not end_date:
            return jsonify({'error': 'Missing required parameters'})
        
        if detector is None:
            return jsonify({'error': 'Anomaly detector not initialized'})
        
        if us_weather_data.empty:
            return jsonify({'error': 'No weather data available'})
        
        # Filter data for the specific station and date range
        station_data = us_weather_data[us_weather_data['STATION'] == station_id].copy()
        
        if station_data.empty:
            return jsonify({'error': f'No data found for station {station_id}'})
        
        # Convert dates and filter
        station_data['DATE'] = pd.to_datetime(station_data['DATE'])
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        filtered_data = station_data[
            (station_data['DATE'] >= start_dt) & 
            (station_data['DATE'] <= end_dt)
        ].copy()
        
        if filtered_data.empty:
            return jsonify({'error': f'No data found for the specified date range'})
        
        # Train models if not already trained
        if not detector.is_trained:
            logger.info("Training anomaly detection models...")
            detector.train_models(filtered_data, optimize=True)
        
        # Run anomaly detection
        logger.info("Running anomaly detection...")
        results = detector.detect_anomalies(
            filtered_data,
            use_statistical='statistical' in methods,
            use_ml='ml' in methods,
            confidence_threshold=confidence_threshold
        )
        
        # Generate anomaly report
        report = generate_anomaly_report(station_id, filtered_data, results)
        
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
        return jsonify({'error': str(e)})

def generate_anomaly_report(station_id, data, results):
    """Generate comprehensive anomaly report"""
    
    report = {
        'station_id': station_id,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_summary': {
            'total_records': len(data),
            'date_range': {
                'start': data['DATE'].min().strftime('%Y-%m-%d'),
                'end': data['DATE'].max().strftime('%Y-%m-%d')
            },
            'temperature_records': data['TMAX'].notna().sum(),
            'precipitation_records': data['PRCP'].notna().sum()
        },
        'anomalies': {},
        'summary': results.get('summary', {}),
        'qa_results': results.get('qa_results', {}),
        'visualizations': {}
    }
    
    # Process statistical anomalies
    if 'statistical' in results:
        stat_anomalies = results['statistical']
        report['anomalies']['statistical'] = {
            'count': len(stat_anomalies),
            'anomalies': stat_anomalies.to_dict('records') if len(stat_anomalies) > 0 else []
        }
    
    # Process ML anomalies
    if 'ml' in results:
        ml_anomalies = results['ml']
        report['anomalies']['ml'] = {}
        
        for model_name, anomalies in ml_anomalies.items():
            report['anomalies']['ml'][model_name] = {
                'count': len(anomalies),
                'anomalies': anomalies.to_dict('records') if len(anomalies) > 0 else []
            }
    
    # Generate visualizations
    try:
        report['visualizations'] = generate_visualizations(data, results)
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
        report['visualizations'] = {}
    
    return report

def generate_visualizations(data, results):
    """Generate visualization plots for the anomaly report"""
    
    visualizations = {}
    
    try:
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 1. Temperature over time with anomalies
        if 'TMAX_F' in data.columns and 'TMIN_F' in data.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot temperature data
            ax.plot(data['DATE'], data['TMAX_F'], label='Max Temp (°F)', alpha=0.7, color='red')
            ax.plot(data['DATE'], data['TMIN_F'], label='Min Temp (°F)', alpha=0.7, color='blue')
            
            # Highlight anomalies
            if 'statistical' in results and len(results['statistical']) > 0:
                stat_anomalies = results['statistical']
                ax.scatter(stat_anomalies['DATE'], stat_anomalies['TMAX_F'], 
                          color='red', s=100, alpha=0.8, label='Temperature Anomalies', marker='x')
            
            ax.set_title('Temperature Over Time with Anomalies')
            ax.set_ylabel('Temperature (°F)')
            ax.legend()
            ax.tick_params(axis='x', rotation=45)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            visualizations['temperature_timeline'] = img_base64
            plt.close()
        
        # 2. Precipitation over time with anomalies
        if 'PRCP_IN' in data.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot precipitation data
            ax.bar(data['DATE'], data['PRCP_IN'], alpha=0.7, color='blue', width=1)
            
            # Highlight anomalies
            if 'statistical' in results and len(results['statistical']) > 0:
                stat_anomalies = results['statistical']
                prcp_anomalies = stat_anomalies[stat_anomalies['PRCP_IN'] > 0]
                if len(prcp_anomalies) > 0:
                    ax.scatter(prcp_anomalies['DATE'], prcp_anomalies['PRCP_IN'], 
                              color='red', s=100, alpha=0.8, label='Precipitation Anomalies', marker='x')
            
            ax.set_title('Precipitation Over Time with Anomalies')
            ax.set_ylabel('Precipitation (inches)')
            ax.legend()
            ax.tick_params(axis='x', rotation=45)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            visualizations['precipitation_timeline'] = img_base64
            plt.close()
        
        # 3. Anomaly summary chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        anomaly_counts = []
        labels = []
        
        if 'statistical' in results:
            anomaly_counts.append(len(results['statistical']))
            labels.append('Statistical')
        
        if 'ml' in results:
            for model_name, anomalies in results['ml'].items():
                anomaly_counts.append(len(anomalies))
                labels.append(f'ML ({model_name})')
        
        if anomaly_counts:
            bars = ax.bar(labels, anomaly_counts, color=['red', 'blue', 'green', 'orange'][:len(labels)])
            ax.set_title('Anomaly Detection Summary')
            ax.set_ylabel('Number of Anomalies')
            
            # Add value labels on bars
            for bar, count in zip(bars, anomaly_counts):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       str(count), ha='center', va='bottom')
            
            ax.tick_params(axis='x', rotation=45)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            visualizations['anomaly_summary'] = img_base64
            plt.close()
        
    except Exception as e:
        logger.error(f"Error in visualization generation: {e}")
    
    return visualizations

@app.route('/api/export-report', methods=['POST'])
def export_report():
    """Export anomaly report as JSON"""
    try:
        data = request.get_json()
        
        # Generate filename
        station_id = data.get('station_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"anomaly_report_{station_id}_{timestamp}.json"
        
        # Save report to file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return jsonify({'filename': filename, 'message': 'Report exported successfully'})
        
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        return jsonify({'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    """Download exported report file"""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({'error': 'File not found'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Load data and initialize detector
    load_data()
    initialize_detector()
    
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🌍 Starting ADDIS - AI-Powered Data Discrepancy Identification System...")
    print("📊 Available stations:", len(us_stations_data) if us_stations_data is not None else 0)
    print("📈 Weather records:", len(us_weather_data) if us_weather_data is not None else 0)
    print("🔍 ADDIS detector:", "Ready" if detector is not None else "Not available")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
