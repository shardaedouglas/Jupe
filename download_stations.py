#!/usr/bin/env python3
"""
ADDIS Station Downloader - Command Line Tool
Author: Shardae Douglas
Date: 2025

Simple command-line interface for downloading weather station data
"""

import sys
import argparse
from station_downloader import StationDownloader
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description='Download weather station data for ADDIS')
    parser.add_argument('--stations', '-s', nargs='+', help='Station IDs to download')
    parser.add_argument('--country', '-c', default='US', help='Country code (default: US)')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Limit number of stations to show')
    parser.add_argument('--start-year', type=int, help='Start year for data')
    parser.add_argument('--end-year', type=int, help='End year for data')
    parser.add_argument('--list', action='store_true', help='List available stations')
    parser.add_argument('--download', action='store_true', help='Download station data')
    
    args = parser.parse_args()
    
    downloader = StationDownloader()
    
    print("ADDIS Station Downloader")
    print("=" * 50)
    
    if args.list:
        # List available stations
        print(f"Fetching available stations for country: {args.country}")
        stations_df = downloader.get_available_stations(args.country, args.limit)
        
        if stations_df.empty:
            print("No stations found")
            return
        
        print(f"Found {len(stations_df)} stations")
        print("\nAvailable Stations:")
        print(stations_df[['ID', 'NAME', 'STATE', 'LATITUDE', 'LONGITUDE']].to_string(index=False))
        
        if not args.download:
            print(f"\nTo download stations, use: python {sys.argv[0]} --download --stations STATION_ID1 STATION_ID2")
            return
    
    if args.download:
        if not args.stations:
            print("Please specify station IDs to download using --stations")
            return
        
        print(f"Downloading data for stations: {', '.join(args.stations)}")
        
        all_data = []
        for station_id in args.stations:
            print(f"\nDownloading {station_id}...")
            data = downloader.download_station_data(station_id, args.start_year, args.end_year)
            
            if not data.empty:
                print(f"Downloaded {len(data)} records")
                all_data.append(data)
                
                # Save individual file
                filename = downloader.save_station_data(data, station_id)
                print(f"Saved to: {filename}")
            else:
                print(f"No data found for {station_id}")
        
        # Combine and save all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_file = downloader.save_station_data(combined_df, "combined", "downloaded_stations.csv")
            
            summary = downloader.get_station_summary(combined_df)
            print(f"\nSummary:")
            print(f"Total records: {summary['total_records']}")
            print(f"Stations: {summary['stations']}")
            print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
            print(f"Elements: {', '.join(summary['elements_available'])}")
            print(f"Combined file: {combined_file}")
        else:
            print("No data downloaded")

if __name__ == "__main__":
    main()
