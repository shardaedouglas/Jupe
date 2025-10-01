# ADDIS Station Download System

## Overview

The ADDIS Station Download System allows you to download weather station data from the National Centers for Environmental Information (NCEI) GHCN-Daily database and integrate it into your ADDIS anomaly detection system.

## Features

- **Station Discovery**: Browse and search available weather stations
- **Bulk Download**: Download multiple stations at once
- **Data Processing**: Automatic conversion to ADDIS format with GHCN flag processing
- **Web Interface**: User-friendly interface for station management
- **Command Line Tool**: Scriptable station downloading
- **Data Persistence**: Save downloaded data for future use

## Components

### 1. Station Downloader (`station_downloader.py`)

Core module for downloading and processing station data from NCEI.

**Key Features:**
- Downloads station metadata from NCEI
- Fetches weather data for specific stations
- Processes GHCN-Daily format files
- Converts data to ADDIS-compatible format
- Handles GHCN quality control flags

### 2. Web Interface Integration

The Flask web application includes a new "Station Management" section with:

- **Search Stations**: Find stations by name or ID
- **Select Multiple Stations**: Checkbox interface for bulk operations
- **Download Progress**: Visual progress indicators
- **Load Existing Data**: Import previously downloaded stations

### 3. Command Line Tool (`download_stations.py`)

Scriptable interface for station downloading.

## Usage

### Web Interface

1. **Open ADDIS**: Navigate to `http://localhost:5001`
2. **Station Management**: Scroll to the "Station Management" section
3. **Search Stations**: Enter a search term and click "Search Stations"
4. **Select Stations**: Check the stations you want to download
5. **Download**: Click "Download Selected Stations"
6. **Monitor Progress**: Watch the progress bar during download

### Command Line Interface

#### List Available Stations
```bash
python download_stations.py --list --limit 10
```

#### Download Specific Stations
```bash
python download_stations.py --download --stations USC00086700 USC00012345
```

#### Download with Date Range
```bash
python download_stations.py --download --stations USC00086700 --start-year 2020 --end-year 2023
```

#### Download from Different Country
```bash
python download_stations.py --list --country CA --limit 5
```

### API Endpoints

#### Get Available Stations
```http
GET /api/stations/available?country=US&limit=100
```

#### Download Stations
```http
POST /api/stations/download
Content-Type: application/json

{
    "station_ids": ["USC00086700", "USC00012345"],
    "start_year": 2020,
    "end_year": 2023
}
```

#### Load Existing Stations
```http
GET /api/stations/load-existing
```

## Data Format

Downloaded station data includes:

### Weather Elements
- **TMAX**: Maximum temperature (°C, converted to °F)
- **TMIN**: Minimum temperature (°C, converted to °F)
- **PRCP**: Precipitation (mm, converted to inches)

### GHCN Quality Flags
- **MFLAG**: Measurement flags
- **QFLAG**: Quality control flags
- **SFLAG**: Source flags
- **Quality Score**: Calculated quality score (0-100)

### Metadata
- **Station ID**: Unique station identifier
- **Date**: Observation date
- **Location**: Latitude, longitude, elevation
- **Station Name**: Human-readable station name

## File Structure

```
Datasets/GHCN_Data/
├── ghcnd-stations.txt          # Station metadata
├── USC00086700_data.csv        # Individual station data
├── USC00012345_data.csv        # Individual station data
├── downloaded_stations.csv      # Combined data
└── all_stations_data.csv       # All downloaded data
```

## Configuration

### API Token (Optional)

For enhanced API access, set your NCEI API token:

1. Get a free API token from [NCEI](https://www.ncei.noaa.gov/cdo-web/)
2. Update `station_downloader.py`:
   ```python
   self.api_token = "YOUR_ACTUAL_TOKEN_HERE"
   ```

### Rate Limiting

The system includes built-in rate limiting to respect NCEI's terms of service:
- 1 second delay between requests
- Automatic retry logic
- Graceful error handling

## Error Handling

The system handles various error conditions:

- **Network Issues**: Automatic retry with exponential backoff
- **Missing Data**: Graceful handling of stations with no data
- **Invalid Stations**: Clear error messages for non-existent stations
- **File Errors**: Robust file parsing with error recovery

## Performance Considerations

### Download Speed
- Direct file access is faster than API calls
- Bulk downloads are more efficient than individual requests
- Rate limiting prevents service disruption

### Storage Requirements
- Each station typically contains 1,000-10,000 records
- Average file size: 100KB-1MB per station
- Plan for 1-10MB per station depending on data range

### Memory Usage
- Individual station processing uses minimal memory
- Bulk operations may require more RAM for large datasets
- Data is processed in chunks to minimize memory footprint

## Troubleshooting

### Common Issues

#### "No stations found"
- Check internet connection
- Verify country code is correct
- Try reducing the limit parameter

#### "No data found for station"
- Station may not have data for the specified date range
- Station may be inactive or discontinued
- Try a different date range

#### "Download failed"
- Check network connectivity
- Verify station IDs are correct
- Try downloading fewer stations at once

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with ADDIS

Downloaded stations are automatically integrated into the ADDIS system:

1. **Data Processing**: GHCN flags are processed and quality scores calculated
2. **Station List**: New stations appear in the station dropdown
3. **Anomaly Detection**: All downloaded data is available for analysis
4. **Quality Flags**: GHCN quality information is included in anomaly reports

## Best Practices

### Station Selection
- Start with stations in your area of interest
- Check station metadata for data availability
- Consider station elevation and climate zone

### Data Management
- Download data in manageable chunks
- Keep backups of downloaded data
- Regularly update station data

### Performance Optimization
- Use date ranges to limit data volume
- Download only necessary weather elements
- Monitor disk space usage

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the error logs
3. Verify your internet connection
4. Ensure you have sufficient disk space


