#!/usr/bin/env python3
"""
Quick GHCN-Daily Metadata Downloader

Simple script to quickly download essential GHCN-Daily metadata files.

Usage:
    python quick_ghcn_download.py

Author: Shardae Douglas
Date: 2025
"""

import requests
import os
from pathlib import Path

def download_ghcn_metadata():
    """
    Download essential GHCN-Daily metadata files
    """
    base_url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily"
    output_dir = Path(".")
    
    # Essential metadata files
    files = {
        'stations.txt': 'Station metadata (ID, coordinates, elevation, name)',
        'inventory.txt': 'Inventory metadata (element types, date ranges)', 
        'countries.txt': 'Country codes',
        'readme.txt': 'Data format documentation'
    }
    
    print("🌍 Downloading GHCN-Daily Metadata...")
    print("=" * 50)
    
    downloaded_files = []
    
    for filename, description in files.items():
        url = f"{base_url}/{filename}"
        output_path = output_dir / filename
        
        print(f"\n📥 Downloading {description}...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"   ✅ Downloaded: {filename} ({size_mb:.2f} MB)")
            downloaded_files.append(str(output_path))
            
        except Exception as e:
            print(f"   ❌ Error downloading {filename}: {e}")
    
    print(f"\n🎉 Download completed!")
    print(f"📁 Files saved to: {output_dir.absolute()}")
    print(f"📊 Downloaded {len(downloaded_files)} files")
    
    return downloaded_files

if __name__ == "__main__":
    download_ghcn_metadata()
