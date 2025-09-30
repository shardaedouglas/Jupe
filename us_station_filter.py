#!/usr/bin/env python3
"""
US Station Filter for GHCN-Daily Anomaly Detection

Downloads and filters GHCN-Daily station metadata to focus on US stations only.
Integrates with the anomaly detection system to ensure US-only analysis.

Based on: https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/

Author: Shardae Douglas
Date: 2025
"""

import pandas as pd
import numpy as np
import requests
import os
from pathlib import Path
import logging
from datetime import datetime
import zipfile
import io

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class USStationFilter:
    """
    Downloads and filters GHCN-Daily stations for US-only analysis
    """
    
    def __init__(self, base_url="https://www.ncei.noaa.gov/pub/data/ghcn/daily", output_dir="."):
        """
        Initialize the US station filter
        
        Args:
            base_url (str): Base URL for GHCN-Daily data
            output_dir (str): Directory to store filtered data
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # US station ID prefixes (based on GHCN-Daily format)
        self.us_prefixes = ['US']
        
        logger.info("Initialized US Station Filter")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
    
    def download_stations_metadata(self):
        """
        Download station metadata from GHCN-Daily
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING STATION METADATA")
        logger.info("=" * 60)
        
        url = f"{self.base_url}/ghcnd-stations.txt"
        output_path = self.output_dir / 'ghcnd-stations.txt'
        
        logger.info(f"Downloading from: {url}")
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"✅ Downloaded: {output_path}")
            logger.info(f"File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
            
            return str(output_path)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to download stations metadata: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None
    
    def filter_us_stations(self, stations_file=None):
        """
        Filter stations to US-only based on station ID prefixes
        
        Args:
            stations_file (str): Path to stations file (if None, downloads it)
            
        Returns:
            pd.DataFrame: Filtered US stations
        """
        logger.info("=" * 60)
        logger.info("FILTERING US STATIONS")
        logger.info("=" * 60)
        
        # Download stations file if not provided
        if stations_file is None:
            stations_file = self.download_stations_metadata()
            if stations_file is None:
                logger.error("Failed to download stations metadata")
                return None
        
        try:
            # Read stations file (fixed-width format)
            logger.info("Reading stations metadata...")
            stations_df = pd.read_fwf(
                stations_file,
                colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)],
                names=['STATION_ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'STATE', 'STATION_NAME'],
                dtype={'LATITUDE': float, 'LONGITUDE': float, 'ELEVATION': float}
            )
            
            logger.info(f"Total stations in dataset: {len(stations_df):,}")
            
            # Filter for US stations (station ID starts with 'US')
            us_stations = stations_df[stations_df['STATION_ID'].str.startswith('US')].copy()
            
            logger.info(f"US stations found: {len(us_stations):,}")
            
            # Additional US geographic bounds validation
            # US bounds: roughly 24.5°N to 71.5°N, 66.9°W to 172.4°W
            us_stations = us_stations[
                (us_stations['LATITUDE'] >= 24.5) & 
                (us_stations['LATITUDE'] <= 71.5) &
                (us_stations['LONGITUDE'] >= -172.4) & 
                (us_stations['LONGITUDE'] <= -66.9)
            ].copy()
            
            logger.info(f"US stations after geographic validation: {len(us_stations):,}")
            
            # Save filtered US stations
            us_stations_path = self.output_dir / 'us_stations.csv'
            us_stations.to_csv(us_stations_path, index=False)
            
            # Generate US stations summary
            self._generate_us_summary(us_stations)
            
            logger.info(f"💾 US stations saved: {us_stations_path}")
            
            return us_stations
            
        except Exception as e:
            logger.error(f"❌ Error filtering US stations: {e}")
            return None
    
    def download_us_inventory(self, us_stations_df):
        """
        Download inventory data for US stations only
        
        Args:
            us_stations_df (pd.DataFrame): US stations dataframe
            
        Returns:
            pd.DataFrame: US stations inventory
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING US STATIONS INVENTORY")
        logger.info("=" * 60)
        
        url = f"{self.base_url}/ghcnd-inventory.txt"
        
        logger.info(f"Downloading inventory from: {url}")
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Read inventory file (fixed-width format)
            logger.info("Reading inventory metadata...")
            inventory_df = pd.read_fwf(
                io.StringIO(response.text),
                colspecs=[(0, 11), (12, 20), (21, 30), (31, 35), (36, 44), (45, 53)],
                names=['STATION_ID', 'LATITUDE', 'LONGITUDE', 'ELEMENT', 'FIRST_YEAR', 'LAST_YEAR'],
                dtype={'LATITUDE': float, 'LONGITUDE': float, 'FIRST_YEAR': int, 'LAST_YEAR': int}
            )
            
            logger.info(f"Total inventory records: {len(inventory_df):,}")
            
            # Filter for US stations
            us_station_ids = set(us_stations_df['STATION_ID'])
            us_inventory = inventory_df[inventory_df['STATION_ID'].isin(us_station_ids)].copy()
            
            logger.info(f"US inventory records: {len(us_inventory):,}")
            
            # Save US inventory
            us_inventory_path = self.output_dir / 'us_inventory.csv'
            us_inventory.to_csv(us_inventory_path, index=False)
            
            # Generate inventory summary
            self._generate_inventory_summary(us_inventory)
            
            logger.info(f"💾 US inventory saved: {us_inventory_path}")
            
            return us_inventory
            
        except Exception as e:
            logger.error(f"❌ Error downloading US inventory: {e}")
            return None
    
    def filter_existing_data(self, data_file, us_stations_df):
        """
        Filter existing weather data to US stations only
        
        Args:
            data_file (str): Path to existing weather data CSV
            us_stations_df (pd.DataFrame): US stations dataframe
            
        Returns:
            pd.DataFrame: Filtered US weather data
        """
        logger.info("=" * 60)
        logger.info("FILTERING EXISTING WEATHER DATA FOR US STATIONS")
        logger.info("=" * 60)
        
        try:
            # Load existing data
            logger.info(f"Loading data from: {data_file}")
            df = pd.read_csv(data_file)
            
            logger.info(f"Original data shape: {df.shape}")
            logger.info(f"Original stations: {df['STATION'].nunique()}")
            
            # Get US station IDs
            us_station_ids = set(us_stations_df['STATION_ID'])
            
            # Filter data for US stations
            us_data = df[df['STATION'].isin(us_station_ids)].copy()
            
            logger.info(f"US data shape: {us_data.shape}")
            logger.info(f"US stations in data: {us_data['STATION'].nunique()}")
            
            # Save filtered US data
            us_data_path = self.output_dir / 'us_weather_data.csv'
            us_data.to_csv(us_data_path, index=False)
            
            # Generate data summary
            self._generate_data_summary(us_data, us_stations_df)
            
            logger.info(f"💾 US weather data saved: {us_data_path}")
            
            return us_data
            
        except Exception as e:
            logger.error(f"❌ Error filtering existing data: {e}")
            return None
    
    def _generate_us_summary(self, us_stations_df):
        """
        Generate summary statistics for US stations
        """
        summary_path = self.output_dir / 'us_stations_summary.txt'
        
        # Calculate statistics
        stats = {
            'total_us_stations': len(us_stations_df),
            'states': us_stations_df['STATE'].nunique(),
            'lat_range': (us_stations_df['LATITUDE'].min(), us_stations_df['LATITUDE'].max()),
            'lon_range': (us_stations_df['LONGITUDE'].min(), us_stations_df['LONGITUDE'].max()),
            'elevation_range': (us_stations_df['ELEVATION'].min(), us_stations_df['ELEVATION'].max()),
            'avg_elevation': us_stations_df['ELEVATION'].mean(),
            'states_with_most_stations': us_stations_df['STATE'].value_counts().head(10).to_dict()
        }
        
        with open(summary_path, 'w') as f:
            f.write("US GHCN-Daily Stations Summary\n")
            f.write("=" * 35 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total US stations: {stats['total_us_stations']:,}\n")
            f.write(f"States represented: {stats['states']}\n")
            f.write(f"Latitude range: {stats['lat_range'][0]:.2f}° to {stats['lat_range'][1]:.2f}°\n")
            f.write(f"Longitude range: {stats['lon_range'][0]:.2f}° to {stats['lon_range'][1]:.2f}°\n")
            f.write(f"Elevation range: {stats['elevation_range'][0]:.1f} to {stats['elevation_range'][1]:.1f} m\n")
            f.write(f"Average elevation: {stats['avg_elevation']:.1f} m\n\n")
            
            f.write("Top 10 states by station count:\n")
            f.write("-" * 30 + "\n")
            for state, count in stats['states_with_most_stations'].items():
                f.write(f"{state}: {count} stations\n")
        
        logger.info(f"📊 US stations summary saved: {summary_path}")
    
    def _generate_inventory_summary(self, us_inventory_df):
        """
        Generate summary statistics for US inventory
        """
        summary_path = self.output_dir / 'us_inventory_summary.txt'
        
        # Calculate statistics
        element_counts = us_inventory_df['ELEMENT'].value_counts()
        year_range = (us_inventory_df['FIRST_YEAR'].min(), us_inventory_df['LAST_YEAR'].max())
        
        with open(summary_path, 'w') as f:
            f.write("US GHCN-Daily Inventory Summary\n")
            f.write("=" * 35 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total inventory records: {len(us_inventory_df):,}\n")
            f.write(f"Unique US stations: {us_inventory_df['STATION_ID'].nunique():,}\n")
            f.write(f"Year range: {year_range[0]} to {year_range[1]}\n")
            f.write(f"Element types: {len(element_counts)}\n\n")
            
            f.write("Element breakdown:\n")
            f.write("-" * 20 + "\n")
            for element, count in element_counts.items():
                f.write(f"{element}: {count:,} records\n")
        
        logger.info(f"📊 US inventory summary saved: {summary_path}")
    
    def _generate_data_summary(self, us_data_df, us_stations_df):
        """
        Generate summary statistics for US weather data
        """
        summary_path = self.output_dir / 'us_data_summary.txt'
        
        # Calculate statistics
        stats = {
            'total_records': len(us_data_df),
            'unique_stations': us_data_df['STATION'].nunique(),
            'date_range': (us_data_df['DATE'].min(), us_data_df['DATE'].max()),
            'temp_coverage': {
                'TMAX_records': us_data_df['TMAX'].notna().sum(),
                'TMIN_records': us_data_df['TMIN'].notna().sum()
            },
            'prcp_coverage': us_data_df['PRCP'].notna().sum(),
            'stations_with_temp': us_data_df[us_data_df['TMAX'].notna()]['STATION'].nunique(),
            'stations_with_prcp': us_data_df[us_data_df['PRCP'].notna()]['STATION'].nunique()
        }
        
        with open(summary_path, 'w') as f:
            f.write("US Weather Data Summary\n")
            f.write("=" * 25 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total records: {stats['total_records']:,}\n")
            f.write(f"Unique stations: {stats['unique_stations']:,}\n")
            f.write(f"Date range: {stats['date_range'][0]} to {stats['date_range'][1]}\n\n")
            
            f.write("Data coverage:\n")
            f.write("-" * 15 + "\n")
            f.write(f"TMAX records: {stats['temp_coverage']['TMAX_records']:,}\n")
            f.write(f"TMIN records: {stats['temp_coverage']['TMIN_records']:,}\n")
            f.write(f"PRCP records: {stats['prcp_coverage']:,}\n\n")
            
            f.write("Station coverage:\n")
            f.write("-" * 17 + "\n")
            f.write(f"Stations with temperature data: {stats['stations_with_temp']:,}\n")
            f.write(f"Stations with precipitation data: {stats['stations_with_prcp']:,}\n")
        
        logger.info(f"📊 US data summary saved: {summary_path}")
    
    def create_us_station_mapping(self, us_stations_df, us_inventory_df):
        """
        Create a mapping file for US stations with their capabilities
        
        Args:
            us_stations_df (pd.DataFrame): US stations dataframe
            us_inventory_df (pd.DataFrame): US inventory dataframe
            
        Returns:
            pd.DataFrame: Enhanced US stations mapping
        """
        logger.info("=" * 60)
        logger.info("CREATING US STATION MAPPING")
        logger.info("=" * 60)
        
        try:
            # Create station capabilities summary
            station_capabilities = us_inventory_df.groupby('STATION_ID')['ELEMENT'].apply(list).reset_index()
            station_capabilities['ELEMENTS'] = station_capabilities['ELEMENT'].apply(lambda x: ', '.join(sorted(set(x))))
            station_capabilities['ELEMENT_COUNT'] = station_capabilities['ELEMENT'].apply(lambda x: len(set(x)))
            
            # Merge with station metadata
            us_mapping = us_stations_df.merge(
                station_capabilities[['STATION_ID', 'ELEMENTS', 'ELEMENT_COUNT']], 
                on='STATION_ID', 
                how='left'
            )
            
            # Add data quality indicators
            us_mapping['HAS_TEMP'] = us_mapping['ELEMENTS'].str.contains('TMAX|TMIN', na=False)
            us_mapping['HAS_PRCP'] = us_mapping['ELEMENTS'].str.contains('PRCP', na=False)
            us_mapping['HAS_SNOW'] = us_mapping['ELEMENTS'].str.contains('SNOW|SNWD', na=False)
            
            # Save enhanced mapping
            mapping_path = self.output_dir / 'us_station_mapping.csv'
            us_mapping.to_csv(mapping_path, index=False)
            
            logger.info(f"💾 US station mapping saved: {mapping_path}")
            
            # Generate mapping summary
            self._generate_mapping_summary(us_mapping)
            
            return us_mapping
            
        except Exception as e:
            logger.error(f"❌ Error creating US station mapping: {e}")
            return None
    
    def _generate_mapping_summary(self, us_mapping_df):
        """
        Generate summary for US station mapping
        """
        summary_path = self.output_dir / 'us_mapping_summary.txt'
        
        with open(summary_path, 'w') as f:
            f.write("US Station Mapping Summary\n")
            f.write("=" * 28 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total US stations: {len(us_mapping_df):,}\n")
            f.write(f"Stations with temperature data: {us_mapping_df['HAS_TEMP'].sum():,}\n")
            f.write(f"Stations with precipitation data: {us_mapping_df['HAS_PRCP'].sum():,}\n")
            f.write(f"Stations with snow data: {us_mapping_df['HAS_SNOW'].sum():,}\n\n")
            
            f.write("Element count distribution:\n")
            f.write("-" * 25 + "\n")
            element_counts = us_mapping_df['ELEMENT_COUNT'].value_counts().sort_index()
            for count, stations in element_counts.items():
                f.write(f"{count} elements: {stations:,} stations\n")
        
        logger.info(f"📊 US mapping summary saved: {summary_path}")
    
    def process_all(self, existing_data_file=None):
        """
        Process all US station filtering steps
        
        Args:
            existing_data_file (str): Path to existing weather data (optional)
            
        Returns:
            dict: Results of all processing steps
        """
        logger.info("🚀 Starting US Station Filtering Process...")
        
        results = {}
        
        # Step 1: Filter US stations
        us_stations = self.filter_us_stations()
        results['us_stations'] = us_stations
        
        if us_stations is None:
            logger.error("Failed to filter US stations. Stopping process.")
            return results
        
        # Step 2: Download US inventory
        us_inventory = self.download_us_inventory(us_stations)
        results['us_inventory'] = us_inventory
        
        # Step 3: Create station mapping
        if us_inventory is not None:
            us_mapping = self.create_us_station_mapping(us_stations, us_inventory)
            results['us_mapping'] = us_mapping
        
        # Step 4: Filter existing data (if provided)
        if existing_data_file and os.path.exists(existing_data_file):
            us_data = self.filter_existing_data(existing_data_file, us_stations)
            results['us_data'] = us_data
        
        # Generate final summary
        self._generate_final_summary(results)
        
        logger.info("🎉 US Station Filtering Process Completed!")
        return results
    
    def _generate_final_summary(self, results):
        """
        Generate final summary of all processing results
        """
        summary_path = self.output_dir / 'us_filtering_summary.txt'
        
        with open(summary_path, 'w') as f:
            f.write("US GHCN-Daily Filtering Summary\n")
            f.write("=" * 35 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("Processing Results:\n")
            f.write("-" * 18 + "\n")
            
            if 'us_stations' in results and results['us_stations'] is not None:
                f.write(f"✅ US Stations: {len(results['us_stations']):,} stations\n")
            else:
                f.write("❌ US Stations: Failed\n")
            
            if 'us_inventory' in results and results['us_inventory'] is not None:
                f.write(f"✅ US Inventory: {len(results['us_inventory']):,} records\n")
            else:
                f.write("❌ US Inventory: Failed\n")
            
            if 'us_mapping' in results and results['us_mapping'] is not None:
                f.write(f"✅ US Mapping: {len(results['us_mapping']):,} stations\n")
            else:
                f.write("❌ US Mapping: Failed\n")
            
            if 'us_data' in results and results['us_data'] is not None:
                f.write(f"✅ US Data: {len(results['us_data']):,} records\n")
            else:
                f.write("❌ US Data: Not processed\n")
            
            f.write(f"\nFiles generated in: {self.output_dir.absolute()}\n")
            f.write("\nNext steps:\n")
            f.write("- Use us_weather_data.csv for anomaly detection\n")
            f.write("- Use us_station_mapping.csv for station selection\n")
            f.write("- Review summary files for data quality assessment\n")

def main():
    """
    Main function to run US station filtering
    """
    print("🇺🇸 US GHCN-Daily Station Filter")
    print("=" * 40)
    print("Source: https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/")
    print("=" * 40)
    
    # Initialize filter
    filter_tool = USStationFilter(output_dir=".")
    
    # Ask user for existing data file
    existing_data = input("\nPath to existing weather data CSV (or press Enter to skip): ").strip()
    
    if existing_data and not os.path.exists(existing_data):
        print(f"❌ File not found: {existing_data}")
        existing_data = None
    
    # Process all steps
    results = filter_tool.process_all(existing_data_file=existing_data)
    
    print(f"\n✅ US Station Filtering Completed!")
    print(f"📁 Files saved to: {filter_tool.output_dir.absolute()}")
    
    if 'us_data' in results and results['us_data'] is not None:
        print(f"\n🎯 Ready for anomaly detection with US-only data!")
        print(f"📊 US stations: {results['us_data']['STATION'].nunique():,}")
        print(f"📈 Total records: {len(results['us_data']):,}")
    else:
        print(f"\n📋 Use the generated metadata files to filter your data manually.")

if __name__ == "__main__":
    main()
