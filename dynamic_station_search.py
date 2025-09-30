"""
Dynamic Station Search and Data Fetching for ADDIS
Author: Shardae Douglas
Date: 2025

This module provides dynamic station search capabilities using ghcnd-stations.txt
and real-time data fetching from NCEI.
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
import re
from functools import lru_cache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicStationSearcher:
    """
    Dynamic station search using ghcnd-stations.txt and NCEI data fetching
    """
    
    def __init__(self, stations_file: str = "Datasets/GHCN_Data/ghcnd-stations.txt"):
        """
        Initialize the dynamic station searcher
        
        Args:
            stations_file: Path to the ghcnd-stations.txt file
        """
        self.stations_file = Path(stations_file)
        self.stations_df = None
        self.ncei_base_url = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/"
        
        # Load stations data
        self._load_stations_data()
        
        # Cache for fetched data
        self.data_cache = {}
        self.cache_expiry = 3600  # 1 hour
        
    def _load_stations_data(self):
        """Load and parse the ghcnd-stations.txt file"""
        try:
            if not self.stations_file.exists():
                logger.error(f"Stations file not found: {self.stations_file}")
                return
            
            logger.info(f"Loading stations data from {self.stations_file}")
            
            # Parse fixed-width file
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
            
            self.stations_df = pd.read_fwf(self.stations_file, colspecs=colspecs, header=None)
            self.stations_df.columns = ['ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'STATE', 'NAME', 'GSN_FLAG', 'HCN_FLAG', 'WMO_ID']
            
            # Clean up data
            self.stations_df['LATITUDE'] = pd.to_numeric(self.stations_df['LATITUDE'], errors='coerce')
            self.stations_df['LONGITUDE'] = pd.to_numeric(self.stations_df['LONGITUDE'], errors='coerce')
            self.stations_df['ELEVATION'] = pd.to_numeric(self.stations_df['ELEVATION'], errors='coerce')
            self.stations_df['NAME'] = self.stations_df['NAME'].str.strip()
            
            # Replace -999.9 elevation with NaN
            self.stations_df['ELEVATION'] = self.stations_df['ELEVATION'].replace(-999.9, np.nan)
            
            logger.info(f"Loaded {len(self.stations_df)} stations from ghcnd-stations.txt")
            
        except Exception as e:
            logger.error(f"Error loading stations data: {e}")
            self.stations_df = pd.DataFrame()
    
    def search_stations(self, query: str, country_code: str = None, limit: int = 50) -> List[Dict]:
        """
        Search for stations based on query
        
        Args:
            query: Search query (station name, ID, state, city)
            country_code: Optional country code filter (US, CA, etc.)
            limit: Maximum number of results
            
        Returns:
            List of matching station dictionaries
        """
        if self.stations_df is None or self.stations_df.empty:
            logger.warning("No stations data available")
            return []
        
        try:
            query_lower = query.lower().strip()
            
            # Start with all stations
            filtered_df = self.stations_df.copy()
            
            # Filter by country code if specified
            if country_code:
                filtered_df = filtered_df[filtered_df['ID'].str.startswith(country_code)]
            
            # Search in multiple fields
            search_conditions = (
                filtered_df['ID'].str.lower().str.contains(query_lower, na=False) |
                filtered_df['NAME'].str.lower().str.contains(query_lower, na=False) |
                filtered_df['STATE'].str.lower().str.contains(query_lower, na=False)
            )
            
            # Also search for individual words in station names
            if ' ' in query_lower:
                words = query_lower.split()
                for word in words:
                    word_condition = (
                        filtered_df['NAME'].str.lower().str.contains(word, na=False) |
                        filtered_df['STATE'].str.lower().str.contains(word, na=False)
                    )
                    search_conditions = search_conditions | word_condition
            
            # Apply search conditions
            results_df = filtered_df[search_conditions].head(limit)
            
            # Convert to list of dictionaries
            stations = []
            for _, row in results_df.iterrows():
                station = {
                    'id': str(row['ID']),
                    'name': str(row['NAME']),
                    'latitude': float(row['LATITUDE']) if pd.notna(row['LATITUDE']) else None,
                    'longitude': float(row['LONGITUDE']) if pd.notna(row['LONGITUDE']) else None,
                    'elevation': float(row['ELEVATION']) if pd.notna(row['ELEVATION']) else None,
                    'state': str(row['STATE']) if pd.notna(row['STATE']) else None,
                    'gsn_flag': str(row['GSN_FLAG']) if pd.notna(row['GSN_FLAG']) else None,
                    'hcn_flag': str(row['HCN_FLAG']) if pd.notna(row['HCN_FLAG']) else None,
                    'wmo_id': str(row['WMO_ID']) if pd.notna(row['WMO_ID']) else None
                }
                stations.append(station)
            
            logger.info(f"Found {len(stations)} stations matching '{query}'")
            return stations
            
        except Exception as e:
            logger.error(f"Error searching stations: {e}")
            return []
    
    def fetch_station_data_from_ncei(self, station_id: str, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        Fetch station data from NCEI website
        
        Args:
            station_id: Station ID to fetch data for
            start_year: Start year for data
            end_year: End year for data
            
        Returns:
            DataFrame with station data
        """
        try:
            # Check cache first
            cache_key = f"{station_id}_{start_year}_{end_year}"
            if cache_key in self.data_cache:
                cached_data, timestamp = self.data_cache[cache_key]
                if time.time() - timestamp < self.cache_expiry:
                    logger.info(f"Using cached data for station {station_id}")
                    return cached_data
            
            logger.info(f"Fetching data for station {station_id} from NCEI")
            
            # Try multiple URL patterns for NCEI data
            urls_to_try = [
                f"{self.ncei_base_url}{station_id}.dly",
                f"https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{station_id}.dly",
                f"https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/all/{station_id}.dly"
            ]
            
            data = pd.DataFrame()
            for url in urls_to_try:
                try:
                    logger.info(f"Trying URL: {url}")
                    response = requests.get(url, timeout=30)
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully fetched data from: {url}")
                        data = self._parse_dly_file(response.text, station_id)
                        break
                    elif response.status_code == 404:
                        logger.warning(f"Station file not found at: {url}")
                        continue
                    else:
                        logger.warning(f"HTTP {response.status_code} from: {url}")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Error fetching from {url}: {e}")
                    continue
            
            if data.empty:
                logger.warning(f"No data found for station {station_id} from any NCEI URL")
                return pd.DataFrame()
            
            # Filter by year if specified
            if not data.empty and (start_year or end_year):
                data = self._filter_by_year(data, start_year, end_year)
            
            # Cache the data
            if not data.empty:
                self.data_cache[cache_key] = (data, time.time())
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for station {station_id}: {e}")
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
            
            logger.info(f"Processed {len(result_df)} records for station")
            logger.info(f"Available columns: {list(result_df.columns)}")
            
            # Check if temperature columns exist
            if 'TMAX' in result_df.columns:
                logger.info(f"TMAX column found with {result_df['TMAX'].notna().sum()} non-null values")
            if 'TMIN' in result_df.columns:
                logger.info(f"TMIN column found with {result_df['TMIN'].notna().sum()} non-null values")
            if 'TMAX_F' in result_df.columns:
                logger.info(f"TMAX_F column created with {result_df['TMAX_F'].notna().sum()} non-null values")
            if 'TMIN_F' in result_df.columns:
                logger.info(f"TMIN_F column created with {result_df['TMIN_F'].notna().sum()} non-null values")
            
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
    
    def search_and_fetch_station(self, query: str, country_code: str = None, limit: int = 1) -> Tuple[List[Dict], pd.DataFrame]:
        """
        Search for stations and fetch data for the first match
        
        Args:
            query: Search query
            country_code: Optional country code filter
            limit: Maximum number of stations to search
            
        Returns:
            Tuple of (station_info, station_data)
        """
        try:
            # Search for stations
            stations = self.search_stations(query, country_code, limit)
            
            if not stations:
                logger.warning(f"No stations found for query: {query}")
                return [], pd.DataFrame()
            
            # Get the first station
            station = stations[0]
            station_id = station['id']
            
            # Fetch data for the station
            data = self.fetch_station_data_from_ncei(station_id)
            
            return stations, data
            
        except Exception as e:
            logger.error(f"Error in search_and_fetch_station: {e}")
            return [], pd.DataFrame()
    
    def get_station_summary(self, station_id: str) -> Dict:
        """
        Get summary information for a station
        
        Args:
            station_id: Station ID
            
        Returns:
            Dictionary with station summary
        """
        try:
            # Find station in stations data
            station_info = self.stations_df[self.stations_df['ID'] == station_id]
            
            if station_info.empty:
                return {'error': 'Station not found'}
            
            station = station_info.iloc[0]
            
            # Get data for the station
            data = self.fetch_station_data_from_ncei(station_id)
            
            if data.empty:
                return {
                    'station_id': station_id,
                    'name': station['NAME'],
                    'latitude': station['LATITUDE'],
                    'longitude': station['LONGITUDE'],
                    'elevation': station['ELEVATION'],
                    'state': station['STATE'],
                    'total_records': 0,
                    'date_range': {'start': None, 'end': None},
                    'elements_available': []
                }
            
            # Calculate summary
            elements_available = []
            for element in ['TMAX', 'TMIN', 'PRCP']:
                if element in data.columns and data[element].notna().any():
                    elements_available.append(element)
            
            return {
                'station_id': station_id,
                'name': station['NAME'],
                'latitude': station['LATITUDE'],
                'longitude': station['LONGITUDE'],
                'elevation': station['ELEVATION'],
                'state': station['STATE'],
                'total_records': len(data),
                'date_range': {
                    'start': data['DATE'].min().strftime('%Y-%m-%d'),
                    'end': data['DATE'].max().strftime('%Y-%m-%d')
                },
                'elements_available': elements_available
            }
            
        except Exception as e:
            logger.error(f"Error getting station summary: {e}")
            return {'error': str(e)}


# Global instance
dynamic_searcher = DynamicStationSearcher()
