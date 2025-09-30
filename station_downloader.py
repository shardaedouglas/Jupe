"""
Station Downloader for ADDIS
Author: Shardae Douglas
Date: 2025

This module handles downloading weather station data from NCEI and integrating it
into the ADDIS system.
"""

import pandas as pd
import numpy as np
import requests
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import List, Dict, Optional, Tuple
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StationDownloader:
    """
    Downloads and processes weather station data from NCEI GHCN-Daily
    """
    
    def __init__(self, data_directory: str = "Datasets/GHCN_Data"):
        """
        Initialize the station downloader
        
        Args:
            data_directory: Directory to store downloaded data
        """
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # NCEI URLs
        self.ncei_base_url = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/"
        self.stations_url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
        
        # API configuration
        self.api_token = "YOUR_API_TOKEN_HERE"  # Users need to get their own token
        self.api_base_url = "https://www.ncei.noaa.gov/cdo-web/api/v2/"
        
        # Rate limiting
        self.request_delay = 1.0  # seconds between requests
        
    def get_available_stations(self, country_code: str = "US", limit: int = 1000) -> pd.DataFrame:
        """
        Get list of available stations from NCEI
        
        Args:
            country_code: Country code (e.g., "US", "CA")
            limit: Maximum number of stations to return
            
        Returns:
            DataFrame with station information
        """
        try:
            logger.info(f"Fetching available stations for country: {country_code}")
            
            # Download stations file
            stations_file = self.data_directory / "ghcnd-stations.txt"
            if not stations_file.exists():
                logger.info("Downloading stations metadata...")
                response = requests.get(self.stations_url, timeout=30)
                response.raise_for_status()
                
                with open(stations_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"Downloaded stations metadata to {stations_file}")
            
            # Parse stations file
            stations_df = self._parse_stations_file(stations_file)
            
            # Filter by country code
            if country_code:
                stations_df = stations_df[stations_df['ID'].str.startswith(country_code)]
            
            # Limit results
            if limit:
                stations_df = stations_df.head(limit)
            
            logger.info(f"Found {len(stations_df)} stations for country {country_code}")
            return stations_df
            
        except Exception as e:
            logger.error(f"Error fetching available stations: {e}")
            return pd.DataFrame()
    
    def _parse_stations_file(self, stations_file: Path) -> pd.DataFrame:
        """
        Parse the GHCN stations file
        
        Args:
            stations_file: Path to the stations file
            
        Returns:
            DataFrame with station information
        """
        try:
            # Read fixed-width file
            colspecs = [
                (0, 11),   # ID
                (12, 20),  # LATITUDE
                (21, 30),  # LONGITUDE
                (31, 37),  # ELEVATION
                (38, 40),  # STATE
                (41, 71),  # NAME
                (72, 75),  # GSN FLAG
                (76, 79),  # HCN/CRN FLAG
                (80, 85)   # WMO ID
            ]
            
            df = pd.read_fwf(stations_file, colspecs=colspecs, header=None)
            df.columns = ['ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'STATE', 'NAME', 'GSN_FLAG', 'HCN_FLAG', 'WMO_ID']
            
            # Clean up data
            df['LATITUDE'] = pd.to_numeric(df['LATITUDE'], errors='coerce')
            df['LONGITUDE'] = pd.to_numeric(df['LONGITUDE'], errors='coerce')
            df['ELEVATION'] = pd.to_numeric(df['ELEVATION'], errors='coerce')
            df['NAME'] = df['NAME'].str.strip()
            
            # Replace -999.9 elevation with NaN
            df['ELEVATION'] = df['ELEVATION'].replace(-999.9, np.nan)
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing stations file: {e}")
            return pd.DataFrame()
    
    def download_station_data(self, station_id: str, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        Download data for a specific station
        
        Args:
            station_id: Station ID (e.g., "USC00086700")
            start_year: Start year for data
            end_year: End year for data
            
        Returns:
            DataFrame with station data
        """
        try:
            logger.info(f"Downloading data for station: {station_id}")
            
            # Try API first if token is configured
            if self.api_token != "YOUR_API_TOKEN_HERE":
                data = self._download_via_api(station_id, start_year, end_year)
                if not data.empty:
                    return data
            
            # Fallback to direct file download
            data = self._download_via_file(station_id)
            
            # Filter by year if specified
            if not data.empty and (start_year or end_year):
                data = self._filter_by_year(data, start_year, end_year)
            
            return data
            
        except Exception as e:
            logger.error(f"Error downloading data for station {station_id}: {e}")
            return pd.DataFrame()
    
    def _download_via_api(self, station_id: str, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        Download station data via NCEI API
        
        Args:
            station_id: Station ID
            start_year: Start year
            end_year: End year
            
        Returns:
            DataFrame with station data
        """
        try:
            headers = {'token': self.api_token}
            
            # Build date range
            start_date = f"{start_year or 1900}-01-01"
            end_date = f"{end_year or datetime.now().year}-12-31"
            
            # Download data for each element
            all_data = []
            elements = ['TMAX', 'TMIN', 'PRCP']
            
            for element in elements:
                logger.info(f"Downloading {element} data for {station_id}")
                
                params = {
                    'datasetid': 'GHCND',
                    'stationid': f'GHCND:{station_id}',
                    'datatypeid': element,
                    'startdate': start_date,
                    'enddate': end_date,
                    'limit': 1000,
                    'units': 'metric'
                }
                
                page = 1
                while True:
                    params['offset'] = (page - 1) * 1000
                    
                    response = requests.get(
                        f"{self.api_base_url}data",
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    records = data.get('results', [])
                    
                    if not records:
                        break
                    
                    for record in records:
                        all_data.append({
                            'STATION': station_id,
                            'DATE': pd.to_datetime(record['date']),
                            'ELEMENT': element,
                            'VALUE': record['value'],
                            'ATTRIBUTES': record.get('attributes', '')
                        })
                    
                    if len(records) < 1000:
                        break
                    
                    page += 1
                    time.sleep(self.request_delay)
            
            if all_data:
                df = pd.DataFrame(all_data)
                return self._process_downloaded_data(df)
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error downloading via API: {e}")
            return pd.DataFrame()
    
    def _download_via_file(self, station_id: str) -> pd.DataFrame:
        """
        Download station data via direct file access
        
        Args:
            station_id: Station ID
            
        Returns:
            DataFrame with station data
        """
        try:
            # Try to download the .dly file
            url = f"{self.ncei_base_url}{station_id}.dly"
            
            logger.info(f"Downloading file: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 404:
                logger.warning(f"Station file not found: {station_id}")
                return pd.DataFrame()
            
            response.raise_for_status()
            
            # Parse the .dly file
            return self._parse_dly_file(response.text, station_id)
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return pd.DataFrame()
    
    def _parse_dly_file(self, content: str, station_id: str) -> pd.DataFrame:
        """
        Parse GHCN-Daily .dly file content
        
        Args:
            content: File content
            station_id: Station ID
            
        Returns:
            DataFrame with parsed data
        """
        try:
            records = []
            lines = content.strip().split('\n')
            
            for line in lines:
                if len(line) < 31:  # Minimum line length
                    continue
                
                # Parse fixed-width format
                station = line[0:11].strip()
                year = int(line[11:15])
                month = int(line[15:17])
                element = line[17:21].strip()
                
                # Parse daily values (up to 31 days)
                for day in range(1, 32):
                    start_pos = 21 + (day - 1) * 8
                    if start_pos + 7 >= len(line):
                        break
                    
                    value_str = line[start_pos:start_pos + 5].strip()
                    mflag = line[start_pos + 5:start_pos + 6]
                    qflag = line[start_pos + 6:start_pos + 7]
                    sflag = line[start_pos + 7:start_pos + 8]
                    
                    if value_str and value_str != '-9999':
                        try:
                            value = int(value_str)
                            date = datetime(year, month, day)
                            
                            records.append({
                                'STATION': station,
                                'DATE': date,
                                'ELEMENT': element,
                                'VALUE': value,
                                'ATTRIBUTES': f"{mflag},{qflag},{sflag}"
                            })
                        except ValueError:
                            continue
            
            if records:
                df = pd.DataFrame(records)
                return self._process_downloaded_data(df)
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error parsing .dly file: {e}")
            return pd.DataFrame()
    
    def _process_downloaded_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process downloaded data into ADDIS format
        
        Args:
            df: Raw downloaded data
            
        Returns:
            Processed DataFrame
        """
        try:
            if df.empty:
                return df
            
            # Pivot to get elements as columns
            df_pivot = df.pivot_table(
                index=['STATION', 'DATE'],
                columns='ELEMENT',
                values='VALUE',
                aggfunc='first'
            ).reset_index()
            
            # Get attributes
            df_attrs = df.pivot_table(
                index=['STATION', 'DATE'],
                columns='ELEMENT',
                values='ATTRIBUTES',
                aggfunc='first'
            ).reset_index()
            
            # Merge data and attributes
            df_attrs.columns = [f"{col}_ATTRIBUTES" if col not in ['STATION', 'DATE'] else col for col in df_attrs.columns]
            
            result_df = df_pivot.merge(df_attrs, on=['STATION', 'DATE'], how='left')
            
            # Add date components
            result_df['YEAR'] = result_df['DATE'].dt.year
            result_df['MONTH'] = result_df['DATE'].dt.month
            result_df['DAY'] = result_df['DATE'].dt.day
            
            # Convert temperatures to Fahrenheit
            if 'TMAX' in result_df.columns:
                result_df['TMAX_C'] = result_df['TMAX'] / 10.0
                result_df['TMAX_F'] = (result_df['TMAX_C'] * 9/5) + 32
            
            if 'TMIN' in result_df.columns:
                result_df['TMIN_C'] = result_df['TMIN'] / 10.0
                result_df['TMIN_F'] = (result_df['TMIN_C'] * 9/5) + 32
            
            # Convert precipitation to inches
            if 'PRCP' in result_df.columns:
                result_df['PRCP_MM'] = result_df['PRCP'] / 10.0
                result_df['PRCP_IN'] = result_df['PRCP_MM'] / 25.4
            
            logger.info(f"Processed {len(result_df)} records")
            return result_df
            
        except Exception as e:
            logger.error(f"Error processing downloaded data: {e}")
            return df
    
    def _filter_by_year(self, df: pd.DataFrame, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        Filter data by year range
        
        Args:
            df: DataFrame to filter
            start_year: Start year
            end_year: End year
            
        Returns:
            Filtered DataFrame
        """
        if start_year:
            df = df[df['YEAR'] >= start_year]
        if end_year:
            df = df[df['YEAR'] <= end_year]
        
        return df
    
    def save_station_data(self, df: pd.DataFrame, station_id: str, filename: str = None) -> str:
        """
        Save station data to file
        
        Args:
            df: DataFrame to save
            station_id: Station ID
            filename: Optional filename
            
        Returns:
            Path to saved file
        """
        try:
            if filename is None:
                filename = f"{station_id}_data.csv"
            
            filepath = self.data_directory / filename
            
            df.to_csv(filepath, index=False)
            logger.info(f"Saved {len(df)} records to {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving station data: {e}")
            return ""
    
    def load_existing_data(self) -> pd.DataFrame:
        """
        Load existing station data
        
        Returns:
            Combined DataFrame of all station data
        """
        try:
            data_files = list(self.data_directory.glob("*_data.csv"))
            
            if not data_files:
                logger.info("No existing station data files found")
                return pd.DataFrame()
            
            all_data = []
            for file in data_files:
                try:
                    df = pd.read_csv(file)
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} records from {file.name}")
                except Exception as e:
                    logger.error(f"Error loading {file.name}: {e}")
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Combined {len(combined_df)} total records from {len(all_data)} files")
                return combined_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
            return pd.DataFrame()
    
    def get_station_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics for station data
        
        Args:
            df: Station data DataFrame
            
        Returns:
            Dictionary with summary statistics
        """
        try:
            if df.empty:
                return {}
            
            summary = {
                'total_records': len(df),
                'stations': df['STATION'].nunique(),
                'date_range': {
                    'start': df['DATE'].min().strftime('%Y-%m-%d'),
                    'end': df['DATE'].max().strftime('%Y-%m-%d')
                },
                'elements_available': [],
                'station_list': df['STATION'].unique().tolist()
            }
            
            # Check which elements are available
            elements = ['TMAX', 'TMIN', 'PRCP']
            for element in elements:
                if element in df.columns and df[element].notna().any():
                    summary['elements_available'].append(element)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {}


def download_station_interactive():
    """
    Interactive function to download station data
    """
    downloader = StationDownloader()
    
    print("🌍 ADDIS Station Downloader")
    print("=" * 50)
    
    # Get available stations
    print("Fetching available US stations...")
    stations_df = downloader.get_available_stations("US", limit=100)
    
    if stations_df.empty:
        print("❌ No stations found")
        return
    
    print(f"✅ Found {len(stations_df)} stations")
    print("\nSample stations:")
    print(stations_df[['ID', 'NAME', 'STATE', 'LATITUDE', 'LONGITUDE']].head(10).to_string(index=False))
    
    # Let user select stations
    print("\n" + "=" * 50)
    station_ids = input("Enter station IDs (comma-separated) or 'all' for first 10: ").strip()
    
    if station_ids.lower() == 'all':
        station_ids = stations_df['ID'].head(10).tolist()
    else:
        station_ids = [s.strip() for s in station_ids.split(',')]
    
    # Download data for selected stations
    all_data = []
    for station_id in station_ids:
        print(f"\n📥 Downloading data for {station_id}...")
        data = downloader.download_station_data(station_id)
        
        if not data.empty:
            print(f"✅ Downloaded {len(data)} records")
            all_data.append(data)
            
            # Save individual file
            downloader.save_station_data(data, station_id)
        else:
            print(f"❌ No data found for {station_id}")
    
    # Combine and save all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = downloader.save_station_data(combined_df, "combined", "all_stations_data.csv")
        
        summary = downloader.get_station_summary(combined_df)
        print(f"\n📊 Summary:")
        print(f"Total records: {summary['total_records']}")
        print(f"Stations: {summary['stations']}")
        print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"Elements: {', '.join(summary['elements_available'])}")
        print(f"Saved to: {combined_file}")


if __name__ == "__main__":
    download_station_interactive()
