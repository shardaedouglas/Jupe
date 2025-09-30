#!/usr/bin/env python3
"""
GHCN-Daily Metadata Inventory Downloader

Downloads metadata inventory files from NOAA NCEI GHCN-Daily dataset
and stores them in the application root directory.

Based on: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily

Author: Shardae Douglas
Date: 2025
"""

import os
import requests
import pandas as pd
from datetime import datetime
import zipfile
import tarfile
import gzip
import shutil
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GHCNMetadataDownloader:
    """
    Downloads and processes GHCN-Daily metadata inventory files
    """
    
    def __init__(self, base_url="https://www.ncei.noaa.gov/pub/data/ghcn/daily", output_dir="."):
        """
        Initialize the downloader
        
        Args:
            base_url (str): Base URL for GHCN-Daily data
            output_dir (str): Directory to store downloaded files
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Define metadata files to download
        self.metadata_files = {
            'stations': 'ghcnd-stations.txt',
            'inventory': 'ghcnd-inventory.txt', 
            'countries': 'ghcnd-countries.txt',
            'readme': 'readme.txt',
            'all_data': 'ghcnd_all.tar.gz'  # Complete dataset (large file)
        }
        
        logger.info(f"Initialized GHCN Metadata Downloader")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
    
    def download_file(self, filename, description=""):
        """
        Download a single file from GHCN-Daily
        
        Args:
            filename (str): Name of the file to download
            description (str): Description for logging
            
        Returns:
            str: Path to downloaded file
        """
        url = f"{self.base_url}/{filename}"
        output_path = self.output_dir / filename
        
        logger.info(f"Downloading {description or filename}...")
        logger.info(f"URL: {url}")
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file size for progress tracking
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Show progress for large files
                        if total_size > 0 and downloaded % (1024 * 1024) == 0:  # Every MB
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Progress: {progress:.1f}% ({downloaded // (1024*1024)} MB)")
            
            logger.info(f"✅ Downloaded: {output_path}")
            logger.info(f"File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
            
            return str(output_path)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to download {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading {filename}: {e}")
            return None
    
    def download_stations_metadata(self):
        """
        Download station metadata (stations.txt)
        Contains: Station ID, latitude, longitude, elevation, state, station name
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING STATION METADATA")
        logger.info("=" * 60)
        
        file_path = self.download_file(
            self.metadata_files['stations'],
            "Station metadata (ID, coordinates, elevation, name)"
        )
        
        if file_path:
            self._process_stations_file(file_path)
        
        return file_path
    
    def download_inventory_metadata(self):
        """
        Download inventory metadata (inventory.txt)
        Contains: Station ID, latitude, longitude, element type, begin/end date
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING INVENTORY METADATA")
        logger.info("=" * 60)
        
        file_path = self.download_file(
            self.metadata_files['inventory'],
            "Inventory metadata (element types, date ranges)"
        )
        
        if file_path:
            self._process_inventory_file(file_path)
        
        return file_path
    
    def download_countries_metadata(self):
        """
        Download country codes metadata (countries.txt)
        Contains: Country codes used in station inventory
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING COUNTRIES METADATA")
        logger.info("=" * 60)
        
        file_path = self.download_file(
            self.metadata_files['countries'],
            "Country codes metadata"
        )
        
        if file_path:
            self._process_countries_file(file_path)
        
        return file_path
    
    def download_readme(self):
        """
        Download README file with data format and documentation
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING README DOCUMENTATION")
        logger.info("=" * 60)
        
        file_path = self.download_file(
            self.metadata_files['readme'],
            "README documentation (data format, definitions)"
        )
        
        return file_path
    
    def download_all_data(self, extract=False):
        """
        Download complete GHCN-Daily dataset (ghcnd_all.tar.gz)
        WARNING: This is a very large file (>1GB)
        
        Args:
            extract (bool): Whether to extract the tar.gz file
        """
        logger.info("=" * 60)
        logger.info("DOWNLOADING COMPLETE GHCN-DAILY DATASET")
        logger.info("=" * 60)
        logger.warning("⚠️  WARNING: This is a very large file (>1GB)")
        
        file_path = self.download_file(
            self.metadata_files['all_data'],
            "Complete GHCN-Daily dataset (ALL STATIONS)"
        )
        
        if file_path and extract:
            self._extract_tar_gz(file_path)
        
        return file_path
    
    def _process_stations_file(self, file_path):
        """
        Process and analyze stations metadata file
        """
        logger.info("Processing stations metadata...")
        
        try:
            # Read stations file (fixed-width format)
            stations_df = pd.read_fwf(
                file_path,
                colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)],
                names=['STATION_ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'STATE', 'STATION_NAME'],
                dtype={'LATITUDE': float, 'LONGITUDE': float, 'ELEVATION': float}
            )
            
            # Save as CSV for easier analysis
            csv_path = self.output_dir / 'ghcnd_stations.csv'
            stations_df.to_csv(csv_path, index=False)
            
            # Generate summary statistics
            summary = {
                'total_stations': len(stations_df),
                'countries': stations_df['STATION_ID'].str[:2].nunique(),
                'lat_range': (stations_df['LATITUDE'].min(), stations_df['LATITUDE'].max()),
                'lon_range': (stations_df['LONGITUDE'].min(), stations_df['LONGITUDE'].max()),
                'elevation_range': (stations_df['ELEVATION'].min(), stations_df['ELEVATION'].max())
            }
            
            logger.info(f"📊 Stations Summary:")
            logger.info(f"   Total stations: {summary['total_stations']:,}")
            logger.info(f"   Countries: {summary['countries']}")
            logger.info(f"   Latitude range: {summary['lat_range'][0]:.2f} to {summary['lat_range'][1]:.2f}")
            logger.info(f"   Longitude range: {summary['lon_range'][0]:.2f} to {summary['lon_range'][1]:.2f}")
            logger.info(f"   Elevation range: {summary['elevation_range'][0]:.1f} to {summary['elevation_range'][1]:.1f} m")
            
            # Save summary
            summary_path = self.output_dir / 'stations_summary.txt'
            with open(summary_path, 'w') as f:
                f.write("GHCN-Daily Stations Summary\n")
                f.write("=" * 30 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
            
            logger.info(f"💾 Saved CSV: {csv_path}")
            logger.info(f"💾 Saved summary: {summary_path}")
            
        except Exception as e:
            logger.error(f"❌ Error processing stations file: {e}")
    
    def _process_inventory_file(self, file_path):
        """
        Process and analyze inventory metadata file
        """
        logger.info("Processing inventory metadata...")
        
        try:
            # Read inventory file (fixed-width format)
            inventory_df = pd.read_fwf(
                file_path,
                colspecs=[(0, 11), (12, 20), (21, 30), (31, 35), (36, 44), (45, 53)],
                names=['STATION_ID', 'LATITUDE', 'LONGITUDE', 'ELEMENT', 'FIRST_YEAR', 'LAST_YEAR'],
                dtype={'LATITUDE': float, 'LONGITUDE': float, 'FIRST_YEAR': int, 'LAST_YEAR': int}
            )
            
            # Save as CSV
            csv_path = self.output_dir / 'ghcnd_inventory.csv'
            inventory_df.to_csv(csv_path, index=False)
            
            # Generate summary statistics
            element_counts = inventory_df['ELEMENT'].value_counts()
            year_range = (inventory_df['FIRST_YEAR'].min(), inventory_df['LAST_YEAR'].max())
            
            logger.info(f"📊 Inventory Summary:")
            logger.info(f"   Total records: {len(inventory_df):,}")
            logger.info(f"   Unique stations: {inventory_df['STATION_ID'].nunique():,}")
            logger.info(f"   Year range: {year_range[0]} to {year_range[1]}")
            logger.info(f"   Element types: {len(element_counts)}")
            
            logger.info(f"📈 Element breakdown:")
            for element, count in element_counts.head(10).items():
                logger.info(f"   {element}: {count:,} records")
            
            # Save summary
            summary_path = self.output_dir / 'inventory_summary.txt'
            with open(summary_path, 'w') as f:
                f.write("GHCN-Daily Inventory Summary\n")
                f.write("=" * 30 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Total records: {len(inventory_df):,}\n")
                f.write(f"Unique stations: {inventory_df['STATION_ID'].nunique():,}\n")
                f.write(f"Year range: {year_range[0]} to {year_range[1]}\n")
                f.write(f"Element types: {len(element_counts)}\n\n")
                f.write("Element breakdown:\n")
                for element, count in element_counts.items():
                    f.write(f"  {element}: {count:,} records\n")
            
            logger.info(f"💾 Saved CSV: {csv_path}")
            logger.info(f"💾 Saved summary: {summary_path}")
            
        except Exception as e:
            logger.error(f"❌ Error processing inventory file: {e}")
    
    def _process_countries_file(self, file_path):
        """
        Process and analyze countries metadata file
        """
        logger.info("Processing countries metadata...")
        
        try:
            # Read countries file (fixed-width format)
            countries_df = pd.read_fwf(
                file_path,
                colspecs=[(0, 2), (3, 50)],
                names=['COUNTRY_CODE', 'COUNTRY_NAME']
            )
            
            # Save as CSV
            csv_path = self.output_dir / 'ghcnd_countries.csv'
            countries_df.to_csv(csv_path, index=False)
            
            logger.info(f"📊 Countries Summary:")
            logger.info(f"   Total countries: {len(countries_df)}")
            
            logger.info(f"💾 Saved CSV: {csv_path}")
            
        except Exception as e:
            logger.error(f"❌ Error processing countries file: {e}")
    
    def _extract_tar_gz(self, file_path):
        """
        Extract tar.gz file
        
        Args:
            file_path (str): Path to tar.gz file
        """
        logger.info(f"Extracting {file_path}...")
        
        try:
            extract_dir = self.output_dir / 'ghcnd_data'
            extract_dir.mkdir(exist_ok=True)
            
            with tarfile.open(file_path, 'r:gz') as tar:
                tar.extractall(extract_dir)
            
            logger.info(f"✅ Extracted to: {extract_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting {file_path}: {e}")
    
    def download_all_metadata(self, include_all_data=False):
        """
        Download all metadata files
        
        Args:
            include_all_data (bool): Whether to download the complete dataset
        """
        logger.info("🚀 Starting GHCN-Daily metadata download...")
        logger.info(f"📁 Output directory: {self.output_dir.absolute()}")
        
        downloaded_files = []
        
        # Download core metadata files
        files_to_download = [
            ('stations', self.download_stations_metadata),
            ('inventory', self.download_inventory_metadata),
            ('countries', self.download_countries_metadata),
            ('readme', self.download_readme)
        ]
        
        for name, download_func in files_to_download:
            file_path = download_func()
            if file_path:
                downloaded_files.append(file_path)
        
        # Optionally download complete dataset
        if include_all_data:
            file_path = self.download_all_data(extract=False)
            if file_path:
                downloaded_files.append(file_path)
        
        # Generate download summary
        self._generate_download_summary(downloaded_files)
        
        logger.info("🎉 Download completed!")
        return downloaded_files
    
    def _generate_download_summary(self, downloaded_files):
        """
        Generate a summary of downloaded files
        """
        summary_path = self.output_dir / 'download_summary.txt'
        
        with open(summary_path, 'w') as f:
            f.write("GHCN-Daily Metadata Download Summary\n")
            f.write("=" * 40 + "\n")
            f.write(f"Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: {self.base_url}\n")
            f.write(f"Output directory: {self.output_dir.absolute()}\n\n")
            
            f.write("Downloaded files:\n")
            f.write("-" * 20 + "\n")
            
            total_size = 0
            for file_path in downloaded_files:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    f.write(f"{os.path.basename(file_path)}: {size / (1024*1024):.2f} MB\n")
            
            f.write(f"\nTotal size: {total_size / (1024*1024):.2f} MB\n")
            
            f.write("\nFile descriptions:\n")
            f.write("-" * 20 + "\n")
            f.write("ghcnd-stations.txt: Station metadata (ID, coordinates, elevation, name)\n")
            f.write("ghcnd-inventory.txt: Inventory metadata (element types, date ranges)\n")
            f.write("ghcnd-countries.txt: Country codes used in station inventory\n")
            f.write("readme.txt: Data format documentation and definitions\n")
            f.write("ghcnd_all.tar.gz: Complete GHCN-Daily dataset (if downloaded)\n")
            
            f.write("\nGenerated files:\n")
            f.write("-" * 20 + "\n")
            f.write("ghcnd_stations.csv: Stations data in CSV format\n")
            f.write("ghcnd_inventory.csv: Inventory data in CSV format\n")
            f.write("ghcnd_countries.csv: Countries data in CSV format\n")
            f.write("stations_summary.txt: Stations summary statistics\n")
            f.write("inventory_summary.txt: Inventory summary statistics\n")
            f.write("download_summary.txt: This summary file\n")
        
        logger.info(f"📋 Download summary saved: {summary_path}")

def main():
    """
    Main function to run the metadata downloader
    """
    print("🌍 GHCN-Daily Metadata Inventory Downloader")
    print("=" * 50)
    print("Source: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily")
    print("=" * 50)
    
    # Initialize downloader
    downloader = GHCNMetadataDownloader(output_dir=".")
    
    # Ask user what to download
    print("\nWhat would you like to download?")
    print("1. Core metadata files only (stations, inventory, countries, readme)")
    print("2. Core metadata + Complete dataset (WARNING: >1GB)")
    print("3. Custom selection")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        downloaded_files = downloader.download_all_metadata(include_all_data=False)
    elif choice == "2":
        confirm = input("⚠️  This will download >1GB of data. Continue? (y/N): ").strip().lower()
        if confirm == 'y':
            downloaded_files = downloader.download_all_metadata(include_all_data=True)
        else:
            print("Download cancelled.")
            return
    elif choice == "3":
        print("\nAvailable files:")
        for i, (name, filename) in enumerate(downloader.metadata_files.items(), 1):
            print(f"{i}. {name}: {filename}")
        
        selections = input("\nEnter file numbers to download (comma-separated): ").strip()
        try:
            indices = [int(x.strip()) - 1 for x in selections.split(',')]
            files_to_download = list(downloader.metadata_files.items())
            
            downloaded_files = []
            for idx in indices:
                if 0 <= idx < len(files_to_download):
                    name, filename = files_to_download[idx]
                    if name == 'stations':
                        downloaded_files.append(downloader.download_stations_metadata())
                    elif name == 'inventory':
                        downloaded_files.append(downloader.download_inventory_metadata())
                    elif name == 'countries':
                        downloaded_files.append(downloader.download_countries_metadata())
                    elif name == 'readme':
                        downloaded_files.append(downloader.download_readme())
                    elif name == 'all_data':
                        downloaded_files.append(downloader.download_all_data())
        except ValueError:
            print("Invalid selection. Downloading core metadata files only.")
            downloaded_files = downloader.download_all_metadata(include_all_data=False)
    else:
        print("Invalid choice. Downloading core metadata files only.")
        downloaded_files = downloader.download_all_metadata(include_all_data=False)
    
    print(f"\n✅ Download completed! Files saved to: {downloader.output_dir.absolute()}")
    print("\nNext steps:")
    print("- Review the generated CSV files for analysis")
    print("- Check the summary files for statistics")
    print("- Use the metadata for station selection and data validation")

if __name__ == "__main__":
    main()
