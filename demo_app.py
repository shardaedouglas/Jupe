#!/usr/bin/env python3
"""
ADDIS - AI-Powered Data Discrepancy Identification System
Flask App for US Weather Anomaly Detection

A simplified version that works with existing data for demonstration purposes.

Usage:
    python demo_app.py

Author: Shardae Douglas
Date: 2025
"""

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
import requests
from urllib.parse import urljoin
from ghcn_flag_handler import GHCNFlagHandler, enhance_data_with_ghcn_flags, get_ghcn_flag_summary
from station_downloader import StationDownloader
from dynamic_station_search import dynamic_searcher
from comprehensive_anomaly_detector import comprehensive_detector
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'addis-secret-key'

# Global variables
weather_data = None
station_downloader = StationDownloader()
ncei_api_base_url = "https://www.ncei.noaa.gov/cdo-web/api/v2/"
ncei_api_token = "YOUR_API_TOKEN_HERE"  # Users need to get their own token

def fetch_station_data_from_ncei(station_id, start_year=None, end_year=None):
    """
    Fetch historical data for a specific station from NCEI CDO API
    
    Args:
        station_id: Station ID (e.g., 'USC00086700')
        start_year: Start year for data (optional)
        end_year: End year for data (optional)
    
    Returns:
        pandas.DataFrame: Station historical data
    """
    try:
        # For demo purposes, we'll use a fallback to local data if API token is not available
        if ncei_api_token == "YOUR_API_TOKEN_HERE":
            logger.warning("NCEI API token not configured. Using local demo data.")
            return fetch_demo_station_data(station_id, start_year, end_year)
        
        logger.info(f"Fetching data for station {station_id} from NCEI CDO API...")
        
        # Set default date range if not provided
        if not start_year:
            start_year = datetime.now().year - 10
        if not end_year:
            end_year = datetime.now().year
        
        # Construct API request
        headers = {'token': ncei_api_token}
        params = {
            'datasetid': 'GHCND',
            'stationid': f'GHCND:{station_id}',
            'startdate': f'{start_year}-01-01',
            'enddate': f'{end_year}-12-31',
            'units': 'metric',
            'limit': 1000
        }
        
        all_records = []
        offset = 1
        
        while True:
            params['offset'] = offset
            response = requests.get(f"{ncei_api_base_url}data", 
                                  headers=headers, 
                                  params=params, 
                                  timeout=30)
            response.raise_for_status()
            
            data = response.json()
            records = data.get('results', [])
            
            if not records:
                break
                
            all_records.extend(records)
            
            # Check if we have more data
            if len(records) < params['limit']:
                break
                
            offset += params['limit']
            
            # Safety limit to prevent infinite loops
            if offset > 10000:
                break
        
        if not all_records:
            logger.warning(f"No data found for station {station_id}")
            return pd.DataFrame()
        
        # Process the API response
        processed_records = []
        for record in all_records:
            try:
                date_str = record['date']
                datatype = record['datatype']
                value = record['value']
                
                # Skip missing values
                if value is None:
                    continue
                
                # Convert date
                date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                
                # Process different data types
                if datatype == 'TMAX':
                    tmax_c = value / 10.0  # Convert from tenths of degrees
                    tmax_f = (tmax_c * 9/5) + 32
                    
                    processed_records.append({
                        'STATION': station_id,
                        'DATE': date_obj,
                        'TMAX_C': tmax_c,
                        'TMAX_F': tmax_f,
                        'YEAR': date_obj.year,
                        'MONTH': date_obj.month,
                        'DAY': date_obj.day
                    })
                    
                elif datatype == 'TMIN':
                    tmin_c = value / 10.0  # Convert from tenths of degrees
                    tmin_f = (tmin_c * 9/5) + 32
                    
                    processed_records.append({
                        'STATION': station_id,
                        'DATE': date_obj,
                        'TMIN_C': tmin_c,
                        'TMIN_F': tmin_f,
                        'YEAR': date_obj.year,
                        'MONTH': date_obj.month,
                        'DAY': date_obj.day
                    })
                    
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping malformed record: {e}")
                continue
        
        if not processed_records:
            logger.warning(f"No valid data found for station {station_id}")
            return pd.DataFrame()
        
        # Convert to DataFrame and merge records by date
        df = pd.DataFrame(processed_records)
        df = df.groupby(['STATION', 'DATE', 'YEAR', 'MONTH', 'DAY']).agg({
            'TMAX_C': 'first',
            'TMAX_F': 'first',
            'TMIN_C': 'first',
            'TMIN_F': 'first'
        }).reset_index()
        
        logger.info(f"Successfully fetched {len(df)} records for station {station_id}")
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data for station {station_id}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching data for station {station_id}: {e}")
        return pd.DataFrame()

def fetch_demo_station_data(station_id, start_year=None, end_year=None):
    """
    Fallback function to fetch demo data when NCEI API is not available
    """
    try:
        # Use the existing local data as a demo
        global weather_data
        if weather_data is None or weather_data.empty:
            logger.warning("No weather data available for demo")
            return pd.DataFrame()
        
        # Filter for the specific station
        station_data = weather_data[weather_data['STATION'] == station_id].copy()
        
        if station_data.empty:
            logger.warning(f"No data found for station {station_id} in local dataset")
            return pd.DataFrame()
        
        # Apply year filters if provided
        if start_year:
            station_data = station_data[station_data['YEAR'] >= start_year]
        if end_year:
            station_data = station_data[station_data['YEAR'] <= end_year]
        
        # Ensure we have the required columns
        required_cols = ['STATION', 'DATE', 'TMAX_F', 'TMIN_F', 'YEAR', 'MONTH', 'DAY']
        missing_cols = [col for col in required_cols if col not in station_data.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns in demo data: {missing_cols}")
            return pd.DataFrame()
        
        logger.info(f"Using demo data: {len(station_data)} records for station {station_id}")
        return station_data
        
    except Exception as e:
        logger.error(f"Error fetching demo data for station {station_id}: {e}")
        return pd.DataFrame()

def calculate_station_baseline(station_data, target_date):
    """
    Calculate baseline statistics for a station around a specific date
    
    Args:
        station_data: Historical data for the station
        target_date: Date to analyze (datetime object)
    
    Returns:
        dict: Baseline statistics
    """
    try:
        # Get data for the same month over all years (within ±15 days)
        target_month = target_date.month
        target_day = target_date.day
        
        # Create a window around the target date (±15 days)
        baseline_data = station_data[
            (station_data['MONTH'] == target_month) &
            (station_data['DAY'] >= max(1, target_day - 15)) &
            (station_data['DAY'] <= min(31, target_day + 15))
        ].copy()
        
        if len(baseline_data) < 10:  # Need at least 10 data points
            logger.warning(f"Insufficient baseline data for station around {target_date}")
            return None
        
        # Calculate baseline statistics with proper NaN handling
        tmax_data = baseline_data['TMAX_F'].dropna()
        tmin_data = baseline_data['TMIN_F'].dropna()
        
        if len(tmax_data) < 5:  # Need at least 5 valid temperature readings
            logger.warning(f"Insufficient TMAX data for baseline calculation around {target_date}")
            return None
        
        baseline = {
            'tmax_f_mean': float(tmax_data.mean()),
            'tmax_f_std': float(tmax_data.std()),
            'sample_size': len(baseline_data),
            'date_range': {
                'start': baseline_data['DATE'].min().strftime('%Y-%m-%d'),
                'end': baseline_data['DATE'].max().strftime('%Y-%m-%d')
            }
        }
        
        # Add TMIN data if available
        if len(tmin_data) >= 5:
            baseline['tmin_f_mean'] = float(tmin_data.mean())
            baseline['tmin_f_std'] = float(tmin_data.std())
        else:
            baseline['tmin_f_mean'] = None
            baseline['tmin_f_std'] = None
        
        # Check for NaN values
        if pd.isna(baseline['tmax_f_mean']) or pd.isna(baseline['tmax_f_std']):
            logger.warning(f"NaN values in baseline calculation for {target_date}")
            return None
        
        logger.info(f"Calculated baseline for {target_date.strftime('%Y-%m-%d')}: "
                   f"TMAX {baseline['tmax_f_mean']:.1f}°F ±{baseline['tmax_f_std']:.1f}°F "
                   f"(n={baseline['sample_size']})")
        
        return baseline
        
    except Exception as e:
        logger.error(f"Error calculating baseline: {e}")
        return None

def generate_visualizations(data, anomalies):
    """Generate visualization plots for the analysis"""
    try:
        visualizations = {}
        
        # Set up the plotting style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Temperature time series plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot temperature data
        ax.plot(data['DATE'], data['TMAX_F'], 'r-', alpha=0.7, label='Max Temperature (°F)')
        if 'TMIN_F' in data.columns and data['TMIN_F'].notna().any():
            ax.plot(data['DATE'], data['TMIN_F'], 'b-', alpha=0.7, label='Min Temperature (°F)')
        
        # Highlight anomalies
        if anomalies:
            anomaly_dates = [datetime.strptime(anomaly['DATE'], '%Y-%m-%d') for anomaly in anomalies]
            anomaly_values = [anomaly['VALUE'] for anomaly in anomalies]
            ax.scatter(anomaly_dates, anomaly_values, color='red', s=100, alpha=0.8, 
                      label=f'Anomalies ({len(anomalies)})', zorder=5)
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Temperature (°F)')
        ax.set_title('Temperature Analysis with Anomaly Detection')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        visualizations['temperature_analysis'] = image_base64
        plt.close()
        
        # Temperature distribution plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if 'TMAX_F' in data.columns and data['TMAX_F'].notna().any():
            ax.hist(data['TMAX_F'].dropna(), bins=20, alpha=0.7, color='red', 
                   label='Max Temperature Distribution')
        
        if 'TMIN_F' in data.columns and data['TMIN_F'].notna().any():
            ax.hist(data['TMIN_F'].dropna(), bins=20, alpha=0.7, color='blue', 
                   label='Min Temperature Distribution')
        
        ax.set_xlabel('Temperature (°F)')
        ax.set_ylabel('Frequency')
        ax.set_title('Temperature Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        visualizations['temperature_distribution'] = image_base64
        plt.close()
        
        return visualizations
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
        return {}

def load_addis_data():
    """Load ADDIS weather data with GHCN flag processing"""
    global weather_data
    
    try:
        # Load the existing GHCN data
        data_file = "Datasets/GHCN_Data/Training_Data/ghcn_cleaned.csv"
        if os.path.exists(data_file):
            weather_data = pd.read_csv(data_file)
            logger.info(f"Loaded {len(weather_data)} weather records")
            
            # Convert date and add basic features
            weather_data['DATE'] = pd.to_datetime(weather_data['DATE'], format='%m-%d-%Y')
            
            # Add temperature conversions
            weather_data['TMAX_C'] = weather_data['TMAX'] / 10.0
            weather_data['TMIN_C'] = weather_data['TMIN'] / 10.0
            weather_data['TMAX_F'] = (weather_data['TMAX_C'] * 9/5) + 32
            weather_data['TMIN_F'] = (weather_data['TMIN_C'] * 9/5) + 32
            
            # Add precipitation conversion
            weather_data['PRCP_MM'] = weather_data['PRCP'] / 10.0
            weather_data['PRCP_IN'] = weather_data['PRCP_MM'] / 25.4
            weather_data['PRCP_IN'] = weather_data['PRCP_IN'].fillna(0)
            
            # Add temporal features
            weather_data['YEAR'] = weather_data['DATE'].dt.year
            weather_data['MONTH'] = weather_data['DATE'].dt.month
            weather_data['DAY'] = weather_data['DATE'].dt.day
            
            # Process GHCN flags
            logger.info("Processing GHCN quality control flags...")
            weather_data = enhance_data_with_ghcn_flags(weather_data)
            
            # Get flag summary
            flag_summary = get_ghcn_flag_summary(weather_data)
            logger.info(f"GHCN flag processing complete. Elements processed: {flag_summary.get('elements_processed', [])}")
            
            logger.info("ADDIS data loaded successfully")
        else:
            logger.error(f"Data file not found: {data_file}")
            weather_data = pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error loading demo data: {e}")
        weather_data = pd.DataFrame()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/stations')
def get_stations():
    """Get list of available stations"""
    global weather_data
    
    if weather_data is None or weather_data.empty:
        return jsonify({'error': 'No weather data available'})
    
    # Get unique stations
    stations = []
    for station_id in weather_data['STATION'].unique():
        station_data = weather_data[weather_data['STATION'] == station_id].iloc[0]
        stations.append({
            'id': station_id,
            'name': station_data['NAME'],
            'state': 'FL',  # Default state
            'latitude': station_data['LATITUDE'],
            'longitude': station_data['LONGITUDE'],
            'elevation': 50.0  # Default elevation
        })
    
    return jsonify({'stations': stations})

@app.route('/api/station/<station_id>/ncei-data')
def get_station_ncei_data(station_id):
    """Fetch historical data for a station from NCEI"""
    try:
        logger.info(f"Fetching NCEI data for station {station_id}")
        
        # Fetch data from NCEI (last 10 years for efficiency)
        current_year = datetime.now().year
        station_data = fetch_station_data_from_ncei(station_id, 
                                                   start_year=current_year - 10,
                                                   end_year=current_year)
        
        if station_data.empty:
            return jsonify({
                'error': f'No data found for station {station_id}',
                'station_id': station_id
            }), 404
        
        # Calculate summary statistics
        summary = {
            'station_id': station_id,
            'total_records': len(station_data),
            'date_range': {
                'start': station_data['DATE'].min().strftime('%Y-%m-%d'),
                'end': station_data['DATE'].max().strftime('%Y-%m-%d')
            },
            'temperature_stats': {
                'tmax_f_mean': float(station_data['TMAX_F'].mean()),
                'tmax_f_std': float(station_data['TMAX_F'].std()),
                'tmin_f_mean': float(station_data['TMIN_F'].mean()) if station_data['TMIN_F'].notna().any() else None,
                'tmin_f_std': float(station_data['TMIN_F'].std()) if station_data['TMIN_F'].notna().any() else None
            },
            'data_source': 'NCEI',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Convert data to JSON-serializable format
        data_records = []
        for _, row in station_data.iterrows():
            record = {}
            for col, value in row.items():
                if pd.isna(value):
                    record[col] = None
                elif isinstance(value, (np.integer, np.int64)):
                    record[col] = int(value)
                elif isinstance(value, (np.floating, np.float64)):
                    record[col] = float(value)
                elif isinstance(value, pd.Timestamp):
                    record[col] = value.strftime('%Y-%m-%d')
                else:
                    record[col] = value
            data_records.append(record)
        
        return jsonify({
            'station_id': station_id,
            'summary': summary,
            'data': data_records
        })
        
    except Exception as e:
        logger.error(f"Error fetching NCEI data for station {station_id}: {e}")
        return jsonify({
            'error': f'Failed to fetch data for station {station_id}: {str(e)}',
            'station_id': station_id
        }), 500

@app.route('/api/station/<station_id>/ghcn-flags')
def get_station_ghcn_flags(station_id):
    """Get GHCN flag information for a station"""
    global weather_data
    
    if weather_data is None or weather_data.empty:
        return jsonify({'error': 'No weather data available'}), 404
    
    try:
        # Filter data for the station
        station_data = weather_data[weather_data['STATION'] == station_id].copy()
        
        if station_data.empty:
            return jsonify({'error': f'No data found for station {station_id}'}), 404
        
        # Get GHCN flag summary
        flag_summary = get_ghcn_flag_summary(station_data)
        
        # Get detailed flag information
        handler = GHCNFlagHandler()
        
        flag_details = {}
        elements = ['PRCP', 'TMAX', 'TMIN']
        
        for element in elements:
            if f"{element}_ATTRIBUTES" in station_data.columns:
                element_data = station_data[[f"{element}_ATTRIBUTES", f"{element}_MFLAG", f"{element}_QFLAG", f"{element}_SFLAG", f"{element}_QUALITY_SCORE"]].dropna()
                
                if not element_data.empty:
                    # Convert value_counts to regular Python dict with string keys
                    quality_flags_dict = {}
                    for key, value in element_data[f"{element}_QFLAG"].value_counts().items():
                        quality_flags_dict[str(key)] = int(value)
                    
                    source_flags_dict = {}
                    for key, value in element_data[f"{element}_SFLAG"].value_counts().items():
                        source_flags_dict[str(key)] = int(value)
                    
                    measurement_flags_dict = {}
                    for key, value in element_data[f"{element}_MFLAG"].value_counts().items():
                        measurement_flags_dict[str(key)] = int(value)
                    
                    flag_details[element] = {
                        'total_records': int(len(element_data)),
                        'quality_score_stats': {
                            'mean': float(element_data[f"{element}_QUALITY_SCORE"].mean()),
                            'min': float(element_data[f"{element}_QUALITY_SCORE"].min()),
                            'max': float(element_data[f"{element}_QUALITY_SCORE"].max()),
                            'std': float(element_data[f"{element}_QUALITY_SCORE"].std())
                        },
                        'quality_flags': quality_flags_dict,
                        'source_flags': source_flags_dict,
                        'measurement_flags': measurement_flags_dict
                    }
        
        # Ensure flag_summary is JSON serializable
        serializable_summary = {}
        if 'elements_processed' in flag_summary:
            serializable_summary['elements_processed'] = flag_summary['elements_processed']
        
        if 'overall_quality' in flag_summary and flag_summary['overall_quality']:
            overall_quality = flag_summary['overall_quality']
            serializable_summary['overall_quality'] = {
                'average_quality_score': float(overall_quality.get('average_quality_score', 0)),
                'min_quality_score': float(overall_quality.get('min_quality_score', 0)),
                'max_quality_score': float(overall_quality.get('max_quality_score', 0)),
                'total_records': int(overall_quality.get('total_records', 0))
            }
        
        return jsonify({
            'station_id': station_id,
            'flag_summary': serializable_summary,
            'flag_details': flag_details,
            'total_records': int(len(station_data))
        })
        
    except Exception as e:
        logger.error(f"Error getting GHCN flags for station {station_id}: {e}")
        return jsonify({'error': f'Error processing GHCN flags: {str(e)}'}), 500

@app.route('/api/stations/available')
def get_available_stations():
    """Get list of available stations from NCEI"""
    try:
        country_code = request.args.get('country', 'US')
        limit = int(request.args.get('limit', 100))
        
        stations_df = station_downloader.get_available_stations(country_code, limit)
        
        if stations_df.empty:
            return jsonify({'error': 'No stations found'}), 404
        
        # Convert to JSON-serializable format
        stations_list = []
        for _, row in stations_df.iterrows():
            stations_list.append({
                'id': str(row['ID']),
                'name': str(row['NAME']),
                'latitude': float(row['LATITUDE']) if pd.notna(row['LATITUDE']) else None,
                'longitude': float(row['LONGITUDE']) if pd.notna(row['LONGITUDE']) else None,
                'elevation': float(row['ELEVATION']) if pd.notna(row['ELEVATION']) else None,
                'state': str(row['STATE']) if pd.notna(row['STATE']) else None,
                'gsn_flag': str(row['GSN_FLAG']) if pd.notna(row['GSN_FLAG']) else None,
                'hcn_flag': str(row['HCN_FLAG']) if pd.notna(row['HCN_FLAG']) else None
            })
        
        return jsonify({
            'stations': stations_list,
            'total': len(stations_list),
            'country': country_code
        })
        
    except Exception as e:
        logger.error(f"Error getting available stations: {e}")
        return jsonify({'error': f'Error fetching stations: {str(e)}'}), 500

@app.route('/api/stations/download', methods=['POST'])
def download_stations():
    """Download data for specified stations"""
    try:
        data = request.get_json()
        station_ids = data.get('station_ids', [])
        start_year = data.get('start_year')
        end_year = data.get('end_year')
        
        if not station_ids:
            return jsonify({'error': 'No station IDs provided'}), 400
        
        logger.info(f"Downloading data for stations: {station_ids}")
        
        downloaded_stations = []
        failed_stations = []
        all_data = []
        
        for station_id in station_ids:
            try:
                logger.info(f"Downloading data for station: {station_id}")
                station_data = station_downloader.download_station_data(station_id, start_year, end_year)
                
                if not station_data.empty:
                    # Process GHCN flags
                    station_data = enhance_data_with_ghcn_flags(station_data)
                    
                    # Save individual station file
                    station_file = station_downloader.save_station_data(station_data, station_id)
                    
                    downloaded_stations.append({
                        'station_id': station_id,
                        'records': len(station_data),
                        'file': station_file,
                        'date_range': {
                            'start': station_data['DATE'].min().strftime('%Y-%m-%d'),
                            'end': station_data['DATE'].max().strftime('%Y-%m-%d')
                        }
                    })
                    
                    all_data.append(station_data)
                else:
                    failed_stations.append({
                        'station_id': station_id,
                        'error': 'No data found'
                    })
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error downloading station {station_id}: {e}")
                failed_stations.append({
                    'station_id': station_id,
                    'error': str(e)
                })
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_file = station_downloader.save_station_data(combined_df, "combined", "downloaded_stations.csv")
            
            # Update global weather data
            global weather_data
            weather_data = combined_df
            
            summary = station_downloader.get_station_summary(combined_df)
            
            return jsonify({
                'success': True,
                'downloaded_stations': downloaded_stations,
                'failed_stations': failed_stations,
                'combined_file': combined_file,
                'summary': summary
            })
        else:
            return jsonify({
                'success': False,
                'downloaded_stations': downloaded_stations,
                'failed_stations': failed_stations,
                'error': 'No data downloaded'
            })
        
    except Exception as e:
        logger.error(f"Error downloading stations: {e}")
        return jsonify({'error': f'Error downloading stations: {str(e)}'}), 500

@app.route('/api/stations/load-existing')
def load_existing_stations():
    """Load existing station data files"""
    try:
        logger.info("Loading existing station data...")
        
        existing_data = station_downloader.load_existing_data()
        
        if existing_data.empty:
            return jsonify({'error': 'No existing station data found'}), 404
        
        # Process GHCN flags
        existing_data = enhance_data_with_ghcn_flags(existing_data)
        
        # Update global weather data
        global weather_data
        weather_data = existing_data
        
        summary = station_downloader.get_station_summary(existing_data)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'message': f'Loaded {summary["total_records"]} records from {summary["stations"]} stations'
        })
        
    except Exception as e:
        logger.error(f"Error loading existing stations: {e}")
        return jsonify({'error': f'Error loading existing stations: {str(e)}'}), 500

@app.route('/api/stations/search')
def search_stations_dynamic():
    """Search stations dynamically from ghcnd-stations.txt"""
    try:
        query = request.args.get('q', '').strip()
        country = request.args.get('country', 'US')
        limit = int(request.args.get('limit', 20))
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        logger.info(f"Searching stations for query: '{query}' in country: {country}")
        
        # Search stations using dynamic searcher
        stations = dynamic_searcher.search_stations(query, country, limit)
        
        if not stations:
            return jsonify({
                'stations': [],
                'total': 0,
                'query': query,
                'country': country,
                'message': f'No stations found matching "{query}"'
            })
        
        return jsonify({
            'stations': stations,
            'total': len(stations),
            'query': query,
            'country': country,
            'message': f'Found {len(stations)} stations matching "{query}"'
        })
        
    except Exception as e:
        logger.error(f"Error searching stations: {e}")
        return jsonify({'error': f'Error searching stations: {str(e)}'}), 500

@app.route('/api/stations/<station_id>/fetch')
def fetch_station_data_dynamic(station_id):
    """Fetch station data dynamically from NCEI"""
    global weather_data
    
    try:
        logger.info(f"Fetching data for station: {station_id}")
        
        # Get station summary
        summary = dynamic_searcher.get_station_summary(station_id)
        
        if 'error' in summary:
            return jsonify({'error': summary['error']}), 404
        
        # Fetch actual data
        data = dynamic_searcher.fetch_station_data_from_ncei(station_id)
        
        if data.empty:
            # Fallback to demo data if NCEI data is not available
            logger.info(f"No NCEI data found for {station_id}, trying demo data fallback")
            try:
                # Try to use existing demo data as fallback
                if not weather_data.empty and station_id in weather_data['STATION'].values:
                    data = weather_data[weather_data['STATION'] == station_id].copy()
                    logger.info(f"Using demo data fallback for {station_id}: {len(data)} records")
                else:
                    return jsonify({
                        'error': f'No data found for station {station_id} from NCEI or local sources',
                        'summary': summary
                    }), 404
            except Exception as e:
                logger.error(f"Error in fallback: {e}")
                return jsonify({
                    'error': f'No data found for station {station_id}',
                    'summary': summary
                }), 404
        
        # Process GHCN flags
        data = enhance_data_with_ghcn_flags(data)
        
        # Update global weather data
        weather_data = data
        
        # Convert data to JSON-serializable format
        data_json = data.to_dict('records')
        for record in data_json:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (np.integer, np.int64)):
                    record[key] = int(value)
                elif isinstance(value, (np.floating, np.float64)):
                    record[key] = float(value)
                elif isinstance(value, pd.Timestamp):
                    record[key] = value.strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'station_id': station_id,
            'summary': summary,
            'data': data_json,
            'total_records': len(data),
            'date_range': {
                'start': data['DATE'].min().strftime('%Y-%m-%d'),
                'end': data['DATE'].max().strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching station data: {e}")
        return jsonify({'error': f'Error fetching station data: {str(e)}'}), 500

@app.route('/api/stations/search-and-fetch')
def search_and_fetch_station():
    """Search for a station and fetch its data in one call"""
    global weather_data
    
    try:
        query = request.args.get('q', '').strip()
        country = request.args.get('country', 'US')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        logger.info(f"Searching and fetching data for query: '{query}'")
        
        # Search and fetch station data
        stations, data = dynamic_searcher.search_and_fetch_station(query, country, limit=1)
        
        if not stations:
            return jsonify({
                'error': f'No stations found matching "{query}"',
                'stations': [],
                'data': []
            }), 404
        
        station = stations[0]
        
        if data.empty:
            # Fallback to demo data if NCEI data is not available
            logger.info(f"No NCEI data found for {station['id']}, trying demo data fallback")
            try:
                # Try to use existing demo data as fallback
                if not weather_data.empty and station['id'] in weather_data['STATION'].values:
                    data = weather_data[weather_data['STATION'] == station['id']].copy()
                    logger.info(f"Using demo data fallback for {station['id']}: {len(data)} records")
                else:
                    return jsonify({
                        'error': f'No data found for station {station["id"]} from NCEI or local sources',
                        'stations': stations,
                        'data': []
                    }), 404
            except Exception as e:
                logger.error(f"Error in fallback: {e}")
                return jsonify({
                    'error': f'No data found for station {station["id"]}',
                    'stations': stations,
                    'data': []
                }), 404
        
        # Process GHCN flags
        data = enhance_data_with_ghcn_flags(data)
        
        # Update global weather data
        weather_data = data
        
        # Convert data to JSON-serializable format
        data_json = data.to_dict('records')
        for record in data_json:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (np.integer, np.int64)):
                    record[key] = int(value)
                elif isinstance(value, (np.floating, np.float64)):
                    record[key] = float(value)
                elif isinstance(value, pd.Timestamp):
                    record[key] = value.strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'stations': stations,
            'selected_station': station,
            'data': data_json,
            'total_records': len(data),
            'date_range': {
                'start': data['DATE'].min().strftime('%Y-%m-%d'),
                'end': data['DATE'].max().strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        logger.error(f"Error in search and fetch: {e}")
        return jsonify({'error': f'Error in search and fetch: {str(e)}'}), 500

@app.route('/api/station/<station_id>/data')
def get_station_data(station_id):
    """Get weather data for a specific station"""
    global weather_data
    
    if weather_data is None or weather_data.empty:
        return jsonify({'error': 'No weather data available'})
    
    # Filter data for the specific station
    station_data = weather_data[weather_data['STATION'] == station_id].copy()
    
    if station_data.empty:
        return jsonify({'error': f'No data found for station {station_id}'})
    
    # Get date range
    date_range = {
        'start': station_data['DATE'].min().strftime('%Y-%m-%d'),
        'end': station_data['DATE'].max().strftime('%Y-%m-%d')
    }
    
    # Get data summary
    summary = {
        'total_records': int(len(station_data)),
        'date_range': date_range,
        'temperature_records': int(station_data['TMAX'].notna().sum()),
        'precipitation_records': int(station_data['PRCP'].notna().sum()),
        'has_metadata': True
    }
    
    # Convert data to JSON-serializable format
    data_records = []
    for _, row in station_data.iterrows():
        record = {}
        for col, value in row.items():
            if pd.isna(value):
                record[col] = None
            elif isinstance(value, (np.integer, np.int64)):
                record[col] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                record[col] = float(value)
            elif isinstance(value, pd.Timestamp):
                record[col] = value.strftime('%Y-%m-%d')
            else:
                record[col] = value
        data_records.append(record)
    
    return jsonify({
        'station_id': station_id,
        'summary': summary,
        'data': data_records
    })

@app.route('/api/anomaly-detection', methods=['POST'])
def run_anomaly_detection():
    """Run simple anomaly detection"""
    global weather_data
    
    try:
        data = request.get_json()
        station_id = data.get('station_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        confidence_threshold = data.get('confidence_threshold', 0.5)
        
        logger.info(f"Running ADDIS anomaly detection for station {station_id}")
        
        # Use the dynamically fetched data that's already loaded
        logger.info("Using dynamically fetched station data for analysis...")
        
        # Check if we have data for this station
        if weather_data.empty or station_id not in weather_data['STATION'].values:
            logger.info(f"No data found for station {station_id}, fetching from NCEI...")
            historical_data = dynamic_searcher.fetch_station_data_from_ncei(station_id)
            
            if historical_data.empty:
                return jsonify({
                    'error': f'No data available for station {station_id}',
                    'station_id': station_id
                }), 404
            
            # Process GHCN flags and update global data
            historical_data = enhance_data_with_ghcn_flags(historical_data)
            weather_data = historical_data
        else:
            # Use existing data
            historical_data = weather_data[weather_data['STATION'] == station_id].copy()
            logger.info(f"Using existing data for station {station_id}: {len(historical_data)} records")
        
        # Parse date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Filter historical data for the analysis period
        analysis_data = historical_data[
            (historical_data['DATE'] >= start_dt) & 
            (historical_data['DATE'] <= end_dt)
        ].copy()
        
        if analysis_data.empty:
            return jsonify({
                'error': f'No data found for station {station_id} in the specified date range',
                'station_id': station_id,
                'date_range': f'{start_date} to {end_date}'
            }), 404
        
        # Check what columns are available
        logger.info(f"Available columns in analysis data: {list(analysis_data.columns)}")
        
        # Check if required temperature columns exist
        if 'TMAX_F' not in analysis_data.columns:
            logger.error("TMAX_F column not found in analysis data")
            logger.info(f"Available elements: {[col for col in analysis_data.columns if col not in ['STATION', 'DATE', 'YEAR', 'MONTH', 'DAY']]}")
            return jsonify({
                'error': 'Temperature data (TMAX_F) not available for this station',
                'available_elements': [col for col in analysis_data.columns if col not in ['STATION', 'DATE', 'YEAR', 'MONTH', 'DAY']],
                'station_id': station_id
            }), 400
        
        if 'TMIN_F' not in analysis_data.columns:
            logger.warning("TMIN_F column not found in analysis data")
        
        # Calculate station-specific baselines for each date
        anomalies = []
        baseline_stats = []
        
        for _, row in analysis_data.iterrows():
            target_date = row['DATE']
            
            # Calculate baseline for this specific date
            baseline = calculate_station_baseline(historical_data, target_date)
            
            if baseline is None:
                continue
            
            baseline_stats.append({
                'date': target_date.strftime('%Y-%m-%d'),
                'baseline': baseline
            })
            
            # Check for temperature anomalies using station-specific baseline
            if pd.notna(row['TMAX_F']) and baseline['tmax_f_std'] > 0:
                z_score = (row['TMAX_F'] - baseline['tmax_f_mean']) / baseline['tmax_f_std']
                
                if abs(z_score) > confidence_threshold:
                    explanation = generate_temperature_explanation(
                        'TMAX_F', row['TMAX_F'], z_score, 
                        baseline['tmax_f_mean'], baseline['tmax_f_std']
                    )
                    
                    # Get GHCN quality information
                    handler = GHCNFlagHandler()
                    tmax_quality_score = row.get('TMAX_QUALITY_SCORE', 100.0)
                    tmax_qflag = row.get('TMAX_QFLAG', '')
                    tmax_sflag = row.get('TMAX_SFLAG', '')
                    
                    anomalies.append({
                        'DATE': target_date.strftime('%Y-%m-%d'),
                        'TYPE': 'Temperature',
                        'VARIABLE': 'TMAX_F',
                        'VALUE': float(row['TMAX_F']),
                        'Z_SCORE': float(z_score),
                        'STATION': str(row['STATION']),
                        'EXPLANATION': explanation,
                        'STATISTICS': {
                            'mean': baseline['tmax_f_mean'],
                            'std': baseline['tmax_f_std'],
                            'threshold': float(confidence_threshold * baseline['tmax_f_std']),
                            'baseline_sample_size': baseline['sample_size']
                        },
                        'GHCN_QUALITY': {
                            'quality_score': float(tmax_quality_score),
                            'quality_flag': tmax_qflag,
                            'source_flag': tmax_sflag,
                            'has_quality_issue': handler.is_quality_issue(tmax_qflag),
                            'is_high_quality_source': handler.is_high_quality_source(tmax_sflag)
                        }
                    })
            
            if (pd.notna(row['TMIN_F']) and 
                baseline['tmin_f_mean'] is not None and 
                baseline['tmin_f_std'] is not None and 
                baseline['tmin_f_std'] > 0):
                
                z_score = (row['TMIN_F'] - baseline['tmin_f_mean']) / baseline['tmin_f_std']
                
                if abs(z_score) > confidence_threshold:
                    explanation = generate_temperature_explanation(
                        'TMIN_F', row['TMIN_F'], z_score,
                        baseline['tmin_f_mean'], baseline['tmin_f_std']
                    )
                    
                    # Get GHCN quality information
                    handler = GHCNFlagHandler()
                    tmin_quality_score = row.get('TMIN_QUALITY_SCORE', 100.0)
                    tmin_qflag = row.get('TMIN_QFLAG', '')
                    tmin_sflag = row.get('TMIN_SFLAG', '')
                    
                    anomalies.append({
                        'DATE': target_date.strftime('%Y-%m-%d'),
                        'TYPE': 'Temperature',
                        'VARIABLE': 'TMIN_F',
                        'VALUE': float(row['TMIN_F']),
                        'Z_SCORE': float(z_score),
                        'STATION': str(row['STATION']),
                        'EXPLANATION': explanation,
                        'STATISTICS': {
                            'mean': baseline['tmin_f_mean'],
                            'std': baseline['tmin_f_std'],
                            'threshold': float(confidence_threshold * baseline['tmin_f_std']),
                            'baseline_sample_size': baseline['sample_size']
                        },
                        'GHCN_QUALITY': {
                            'quality_score': float(tmin_quality_score),
                            'quality_flag': tmin_qflag,
                            'source_flag': tmin_sflag,
                            'has_quality_issue': handler.is_quality_issue(tmin_qflag),
                            'is_high_quality_source': handler.is_high_quality_source(tmin_sflag)
                        }
                    })
        
        # Generate visualizations
        visualizations = generate_visualizations(analysis_data, anomalies)
        
        # Calculate summary statistics
        total_anomalies = len(anomalies)
        data_quality_score = min(100, max(0, 100 - (total_anomalies / len(analysis_data) * 100)))
        
        summary = {
            'station_id': station_id,
            'total_anomalies': total_anomalies,
            'data_quality_score': data_quality_score,
            'confidence_threshold': confidence_threshold,
            'analysis_period': f'{start_date} to {end_date}',
            'baseline_data_points': len(historical_data),
            'analysis_data_points': len(analysis_data),
            'data_source': 'NCEI'
        }
        
        data_summary = {
            'station_id': station_id,
            'total_records': len(analysis_data),
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'temperature_range': {
                'tmax_f_min': float(analysis_data['TMAX_F'].min()),
                'tmax_f_max': float(analysis_data['TMAX_F'].max()),
                'tmin_f_min': float(analysis_data['TMIN_F'].min()) if analysis_data['TMIN_F'].notna().any() else None,
                'tmin_f_max': float(analysis_data['TMIN_F'].max()) if analysis_data['TMIN_F'].notna().any() else None
            }
        }
        
        return jsonify({
            'summary': summary,
            'data_summary': data_summary,
            'anomalies': {
                'statistical': {
                    'count': total_anomalies,
                    'anomalies': anomalies
                }
            },
            'visualizations': visualizations,
            'baseline_stats': baseline_stats
        })
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/comprehensive-anomaly-detection', methods=['POST'])
def run_comprehensive_anomaly_detection():
    """Run comprehensive anomaly detection for all weather elements"""
    global weather_data
    
    try:
        data = request.get_json()
        station_id = data.get('station_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        confidence_threshold = data.get('confidence_threshold', 1.0)
        
        logger.info(f"Running comprehensive ADDIS anomaly detection for station {station_id}")
        
        # Use the dynamically fetched data that's already loaded
        logger.info("Using dynamically fetched station data for comprehensive analysis...")
        
        # Check if we have data for this station
        if weather_data.empty or station_id not in weather_data['STATION'].values:
            logger.info(f"No data found for station {station_id}, fetching from NCEI...")
            historical_data = dynamic_searcher.fetch_station_data_from_ncei(station_id)
            
            if historical_data.empty:
                return jsonify({
                    'error': f'No data available for station {station_id}',
                    'station_id': station_id
                }), 404
            
            # Process GHCN flags and update global data
            historical_data = enhance_data_with_ghcn_flags(historical_data)
            weather_data = historical_data
        else:
            # Use existing data
            historical_data = weather_data[weather_data['STATION'] == station_id].copy()
            logger.info(f"Using existing data for station {station_id}: {len(historical_data)} records")
        
        # Run comprehensive anomaly detection
        results = comprehensive_detector.detect_comprehensive_anomalies(
            historical_data, station_id, start_date, end_date, confidence_threshold
        )
        
        if 'error' in results:
            return jsonify(results), 400
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in comprehensive anomaly detection: {e}")
        return jsonify({'error': f'Error in comprehensive anomaly detection: {str(e)}'}), 500

def detect_simple_anomalies(data, threshold):
    """Simple statistical anomaly detection"""
    anomalies = []
    
    # Temperature anomalies (Z-score method)
    for col in ['TMAX_F', 'TMIN_F']:
        if col in data.columns and data[col].notna().sum() > 0:
            values = data[col].dropna()
            if len(values) > 1:
                z_scores = np.abs((values - values.mean()) / values.std())
                anomaly_mask = z_scores > threshold * 2  # Scale threshold
                
                for idx in values[anomaly_mask].index:
                    value = float(data.loc[idx, col])
                    z_score = float(z_scores[idx])
                    mean_val = float(values.mean())
                    std_val = float(values.std())
                    
                    # Generate explanation for temperature anomaly
                    explanation = generate_temperature_explanation(col, value, z_score, mean_val, std_val)
                    
                    anomalies.append({
                        'DATE': data.loc[idx, 'DATE'].strftime('%Y-%m-%d'),
                        'TYPE': 'Temperature',
                        'VARIABLE': col,
                        'VALUE': value,
                        'Z_SCORE': z_score,
                        'STATION': str(data.loc[idx, 'STATION']),
                        'EXPLANATION': explanation,
                        'STATISTICS': {
                            'mean': mean_val,
                            'std': std_val,
                            'threshold': float(threshold * 2)
                        }
                    })
    
    # Precipitation anomalies
    if 'PRCP_IN' in data.columns and data['PRCP_IN'].notna().sum() > 0:
        prcp_values = data['PRCP_IN'].dropna()
        if len(prcp_values) > 1:
            # Use 95th percentile for precipitation
            threshold_value = prcp_values.quantile(0.95)
            anomaly_mask = prcp_values > threshold_value
            
            for idx in prcp_values[anomaly_mask].index:
                value = float(data.loc[idx, 'PRCP_IN'])
                percentile_95 = float(prcp_values.quantile(0.95))
                percentile_99 = float(prcp_values.quantile(0.99))
                
                # Generate explanation for precipitation anomaly
                explanation = generate_precipitation_explanation(value, percentile_95, percentile_99)
                
                anomalies.append({
                    'DATE': data.loc[idx, 'DATE'].strftime('%Y-%m-%d'),
                    'TYPE': 'Precipitation',
                    'VARIABLE': 'PRCP_IN',
                    'VALUE': value,
                    'THRESHOLD': percentile_95,
                    'STATION': str(data.loc[idx, 'STATION']),
                    'EXPLANATION': explanation,
                    'STATISTICS': {
                        'percentile_95': percentile_95,
                        'percentile_99': percentile_99,
                        'max_value': float(prcp_values.max()),
                        'mean_value': float(prcp_values.mean())
                    }
                })
    
    return anomalies

def generate_temperature_explanation(variable, value, z_score, mean_val, std_val):
    """Generate detailed explanation for temperature anomalies"""
    
    temp_type = "maximum" if "TMAX" in variable else "minimum"
    temp_unit = "°F"
    
    # Determine severity level
    if z_score > 3.0:
        severity = "extreme"
        severity_desc = "This represents an extremely unusual temperature"
    elif z_score > 2.5:
        severity = "severe"
        severity_desc = "This represents a severely unusual temperature"
    else:
        severity = "moderate"
        severity_desc = "This represents a moderately unusual temperature"
    
    # Calculate deviation from mean
    deviation = value - mean_val
    deviation_pct = abs(deviation) / mean_val * 100
    
    # Generate contextual explanation
    if deviation > 0:
        direction = "higher" if temp_type == "maximum" else "warmer"
        direction_desc = f"unusually {direction}"
    else:
        direction = "lower" if temp_type == "maximum" else "colder"
        direction_desc = f"unusually {direction}"
    
    explanation = f"""
    <strong>{severity_desc}</strong> for {temp_type} temperature.
    
    <strong>Key Details:</strong>
    • Recorded {temp_type} temperature: <strong>{value:.1f}{temp_unit}</strong>
    • Historical average: {mean_val:.1f}{temp_unit}
    • Deviation: {deviation:+.1f}{temp_unit} ({deviation_pct:.1f}% from average)
    • Statistical significance: Z-score of {z_score:.2f}
    
    <strong>Why this is anomalous:</strong>
    This {temp_type} temperature is {direction_desc} than 95% of historical values for this station. 
    The Z-score of {z_score:.2f} indicates this value is {abs(deviation):.1f}{temp_unit} away from the mean, 
    which is {z_score:.1f} times the standard deviation ({std_val:.1f}{temp_unit}).
    
    <strong>Possible causes:</strong>
    • Extreme weather event (heat wave, cold snap)
    • Measurement error or equipment malfunction
    • Unusual atmospheric conditions
    • Data entry error
    """
    
    return explanation.strip()

def generate_precipitation_explanation(value, percentile_95, percentile_99):
    """Generate detailed explanation for precipitation anomalies"""
    
    # Determine severity level
    if value >= percentile_99:
        severity = "extreme"
        severity_desc = "This represents an extremely rare precipitation event"
    elif value >= percentile_95:
        severity = "severe"
        severity_desc = "This represents a severely unusual precipitation event"
    else:
        severity = "moderate"
        severity_desc = "This represents a moderately unusual precipitation event"
    
    # Calculate how much above threshold
    excess = value - percentile_95
    excess_pct = (value / percentile_95 - 1) * 100
    
    # Generate contextual explanation
    explanation = f"""
    <strong>{severity_desc}</strong> for daily precipitation.
    
    <strong>Key Details:</strong>
    • Recorded precipitation: <strong>{value:.2f} inches</strong>
    • 95th percentile threshold: {percentile_95:.2f} inches
    • 99th percentile threshold: {percentile_99:.2f} inches
    • Excess above threshold: {excess:.2f} inches ({excess_pct:.1f}% above normal)
    
    <strong>Why this is anomalous:</strong>
    This precipitation amount exceeds the 95th percentile threshold, meaning it's higher than 
    95% of all historical daily precipitation values for this station. This represents a 
    {severity} precipitation event that occurs less than 5% of the time.
    
    <strong>Possible causes:</strong>
    • Severe thunderstorm or tropical system
    • Atmospheric river or moisture plume
    • Measurement error (overflow, blocked gauge)
    • Data entry error
    • Unusual weather pattern
    """
    
    return explanation.strip()

def generate_demo_report(station_id, data, anomalies):
    """Generate demo anomaly report"""
    
    report = {
        'station_id': station_id,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_summary': {
            'total_records': int(len(data)),
            'date_range': {
                'start': data['DATE'].min().strftime('%Y-%m-%d'),
                'end': data['DATE'].max().strftime('%Y-%m-%d')
            },
            'temperature_records': int(data['TMAX'].notna().sum()),
            'precipitation_records': int(data['PRCP'].notna().sum())
        },
        'anomalies': {
            'statistical': {
                'count': int(len(anomalies)),
                'anomalies': anomalies
            }
        },
        'summary': {
            'total_anomalies': int(len(anomalies)),
            'data_quality_score': float(85),  # Demo value
            'confidence_threshold': float(0.5)
        },
        'visualizations': generate_demo_visualizations(data, anomalies)
    }
    
    return report

def generate_demo_visualizations(data, anomalies):
    """Generate demo visualizations"""
    visualizations = {}
    
    try:
        plt.style.use('default')
        
        # Temperature timeline
        if 'TMAX_F' in data.columns and 'TMIN_F' in data.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            ax.plot(data['DATE'], data['TMAX_F'], label='Max Temp (°F)', alpha=0.7, color='red')
            ax.plot(data['DATE'], data['TMIN_F'], label='Min Temp (°F)', alpha=0.7, color='blue')
            
            # Highlight anomalies
            temp_anomalies = [a for a in anomalies if a['TYPE'] == 'Temperature']
            for anomaly in temp_anomalies:
                anomaly_date = pd.to_datetime(anomaly['DATE'])
                ax.scatter(anomaly_date, anomaly['VALUE'], 
                          color='red', s=100, alpha=0.8, marker='x')
            
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
        
        # Precipitation timeline
        if 'PRCP_IN' in data.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            ax.bar(data['DATE'], data['PRCP_IN'], alpha=0.7, color='blue', width=1)
            
            # Highlight anomalies
            prcp_anomalies = [a for a in anomalies if a['TYPE'] == 'Precipitation']
            for anomaly in prcp_anomalies:
                anomaly_date = pd.to_datetime(anomaly['DATE'])
                ax.scatter(anomaly_date, anomaly['VALUE'], 
                          color='red', s=100, alpha=0.8, marker='x')
            
            ax.set_title('Precipitation Over Time with Anomalies')
            ax.set_ylabel('Precipitation (inches)')
            ax.tick_params(axis='x', rotation=45)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            visualizations['precipitation_timeline'] = img_base64
            plt.close()
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
    
    return visualizations

if __name__ == '__main__':
    # Load demo data
    load_addis_data()
    
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    print("🌍 Starting ADDIS - AI-Powered Data Discrepancy Identification System...")
    print("📊 Available records:", len(weather_data) if weather_data is not None else 0)
    print("🌐 Open your browser and go to: http://localhost:5001")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
