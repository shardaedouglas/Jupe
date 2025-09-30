#!/usr/bin/env python3
"""
US Station Filter Runner

Quick script to filter GHCN-Daily data to US stations only and prepare for anomaly detection.

Usage:
    python run_us_filter.py

Author: Shardae Douglas
Date: 2025
"""

import pandas as pd
import numpy as np
import requests
import io
from pathlib import Path
import os

def download_us_stations_metadata():
    """Download US station metadata from GHCN-Daily"""
    base_url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily"
    stations_url = f"{base_url}/ghcnd-stations.txt"
    
    print(f"🌍 Downloading US station metadata from GHCN-Daily...")
    print(f"URL: {stations_url}")
    
    try:
        response = requests.get(stations_url, timeout=30)
        response.raise_for_status()
        
        # Read stations file (fixed-width format)
        stations_df = pd.read_fwf(
            io.StringIO(response.text),
            colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)],
            names=['STATION_ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'STATE', 'STATION_NAME'],
            dtype={'LATITUDE': float, 'LONGITUDE': float, 'ELEVATION': float}
        )
        
        # Filter for US stations
        us_stations_metadata = stations_df[stations_df['STATION_ID'].str.startswith('US')].copy()
        
        print(f"✅ Downloaded {len(us_stations_metadata):,} US stations metadata")
        return us_stations_metadata
        
    except Exception as e:
        print(f"❌ Error downloading metadata: {e}")
        return None

def filter_to_us_stations(data_file, output_file=None):
    """
    Filter existing weather data to US stations only
    
    Args:
        data_file (str): Path to existing weather data CSV
        output_file (str): Path to save filtered data (optional)
    
    Returns:
        pd.DataFrame: Filtered US weather data
    """
    print("=" * 60)
    print("FILTERING TO US STATIONS ONLY")
    print("=" * 60)
    
    # Load existing data
    print(f"📂 Loading data from: {data_file}")
    df = pd.read_csv(data_file)
    
    print(f"Original dataset: {len(df):,} records from {df['STATION'].nunique():,} stations")
    
    # Filter for US stations (station ID starts with 'US')
    df_us = df[df['STATION'].str.startswith('US')].copy()
    
    print(f"US-only dataset: {len(df_us):,} records from {df_us['STATION'].nunique():,} stations")
    print(f"Data reduction: {len(df_us)/len(df)*100:.1f}% of original data")
    
    # Check US station distribution by state
    print(f"\nUS stations by state:")
    try:
        us_state_counts = df_us.groupby('STATION')['NAME'].first().str.split(',').str[1].str.strip().value_counts()
        print(us_state_counts.head(10))
    except:
        print("   State information not available in current format")
    
    # Check data coverage for US stations
    print(f"\nData coverage for US stations:")
    print(f"Temperature data (TMAX): {df_us['TMAX'].notna().sum():,} records ({df_us['TMAX'].notna().sum()/len(df_us)*100:.1f}%)")
    print(f"Temperature data (TMIN): {df_us['TMIN'].notna().sum():,} records ({df_us['TMIN'].notna().sum()/len(df_us)*100:.1f}%)")
    print(f"Precipitation data (PRCP): {df_us['PRCP'].notna().sum():,} records ({df_us['PRCP'].notna().sum()/len(df_us)*100:.1f}%)")
    
    # Save filtered data if output file specified
    if output_file:
        df_us.to_csv(output_file, index=False)
        print(f"💾 US-only data saved to: {output_file}")
    
    return df_us

def enhance_with_metadata(df_us, us_stations_metadata):
    """
    Enhance US data with station metadata
    
    Args:
        df_us (pd.DataFrame): US weather data
        us_stations_metadata (pd.DataFrame): US stations metadata
    
    Returns:
        pd.DataFrame: Enhanced US weather data
    """
    print("=" * 60)
    print("ENHANCING WITH US STATION METADATA")
    print("=" * 60)
    
    # Merge with metadata
    df_enhanced = df_us.merge(
        us_stations_metadata[['STATION_ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'STATE']], 
        left_on='STATION', 
        right_on='STATION_ID', 
        how='left'
    )
    
    print(f"Enhanced dataset:")
    print(f"Records with metadata: {df_enhanced['STATION_ID'].notna().sum():,}")
    print(f"Records without metadata: {df_enhanced['STATION_ID'].isna().sum():,}")
    
    # Show US geographic coverage
    if 'LATITUDE' in df_enhanced.columns and df_enhanced['LATITUDE'].notna().any():
        print(f"\nUS Geographic Coverage:")
        print(f"Latitude range: {df_enhanced['LATITUDE'].min():.2f}° to {df_enhanced['LATITUDE'].max():.2f}°")
        print(f"Longitude range: {df_enhanced['LONGITUDE'].min():.2f}° to {df_enhanced['LONGITUDE'].max():.2f}°")
        print(f"Elevation range: {df_enhanced['ELEVATION'].min():.1f} to {df_enhanced['ELEVATION'].max():.1f} m")
        
        # Show state distribution
        print(f"\nTop 10 states by station count:")
        state_counts = df_enhanced.groupby('STATE')['STATION'].nunique().sort_values(ascending=False)
        print(state_counts.head(10))
    else:
        print("   Geographic metadata not available")
    
    return df_enhanced

def add_us_features(df_enhanced):
    """
    Add US-specific features for anomaly detection
    
    Args:
        df_enhanced (pd.DataFrame): Enhanced US weather data
    
    Returns:
        pd.DataFrame: Data with US-specific features
    """
    print("=" * 60)
    print("ADDING US-SPECIFIC FEATURES")
    print("=" * 60)
    
    data = df_enhanced.copy()
    
    # US Climate Zones (simplified)
    if 'LATITUDE' in data.columns:
        def get_us_climate_zone(lat, lon):
            if lat >= 45:  # Northern tier
                return 'Northern'
            elif lat >= 35:  # Mid-latitude
                return 'Mid-Latitude'
            elif lat >= 25:  # Subtropical
                return 'Subtropical'
            else:  # Tropical
                return 'Tropical'
        
        data['US_CLIMATE_ZONE'] = data.apply(
            lambda row: get_us_climate_zone(row['LATITUDE'], row['LONGITUDE']), axis=1
        )
        
        # Elevation categories
        if 'ELEVATION' in data.columns:
            def get_elevation_category(elevation):
                if elevation < 200:
                    return 'Low'
                elif elevation < 1000:
                    return 'Mid'
                else:
                    return 'High'
            
            data['ELEVATION_CATEGORY'] = data['ELEVATION'].apply(get_elevation_category)
        
        # US-specific seasonal patterns
        data['IS_SUMMER'] = data['MONTH'].isin([6, 7, 8]).astype(int)
        data['IS_WINTER'] = data['MONTH'].isin([12, 1, 2]).astype(int)
        
        print("✅ US-specific features added:")
        us_features = ['US_CLIMATE_ZONE', 'ELEVATION_CATEGORY', 'IS_SUMMER', 'IS_WINTER']
        for feature in us_features:
            if feature in data.columns:
                print(f"   - {feature}")
        
        # Show climate zone distribution
        if 'US_CLIMATE_ZONE' in data.columns:
            print(f"\nUS Climate Zone Distribution:")
            climate_counts = data['US_CLIMATE_ZONE'].value_counts()
            print(climate_counts)
        
        # Show elevation distribution
        if 'ELEVATION_CATEGORY' in data.columns:
            print(f"\nElevation Category Distribution:")
            elevation_counts = data['ELEVATION_CATEGORY'].value_counts()
            print(elevation_counts)
    else:
        print("⚠️  No geographic metadata available for US-specific features")
    
    return data

def main():
    """
    Main function to run US station filtering
    """
    print("🇺🇸 US GHCN-Daily Station Filter")
    print("=" * 40)
    print("Source: https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/")
    print("=" * 40)
    
    # Check for existing data file
    data_file = "Datasets/GHCN_Data/Training_Data/ghcn_cleaned.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("Please ensure the GHCN cleaned data file exists.")
        return
    
    # Step 1: Download US station metadata
    us_stations_metadata = download_us_stations_metadata()
    
    # Step 2: Filter to US stations
    df_us = filter_to_us_stations(data_file, "us_weather_data.csv")
    
    # Step 3: Enhance with metadata
    if us_stations_metadata is not None:
        df_enhanced = enhance_with_metadata(df_us, us_stations_metadata)
        
        # Step 4: Add US-specific features
        df_final = add_us_features(df_enhanced)
        
        # Save final enhanced data
        df_final.to_csv("us_enhanced_weather_data.csv", index=False)
        print(f"\n💾 Final enhanced US data saved to: us_enhanced_weather_data.csv")
        
        print(f"\n📊 Final Summary:")
        print(f"   Total records: {len(df_final):,}")
        print(f"   US stations: {df_final['STATION'].nunique():,}")
        print(f"   Features: {len(df_final.columns)}")
        print(f"   US-specific features: {len([col for col in df_final.columns if 'US_' in col or 'CLIMATE' in col or 'ELEVATION' in col])}")
        
        print(f"\n🎯 Ready for US-focused anomaly detection!")
        print(f"📁 Use 'us_enhanced_weather_data.csv' in your anomaly detection notebook")
    else:
        print(f"\n⚠️  Continuing with basic US filtering only")
        print(f"📁 Use 'us_weather_data.csv' in your anomaly detection notebook")

if __name__ == "__main__":
    main()
