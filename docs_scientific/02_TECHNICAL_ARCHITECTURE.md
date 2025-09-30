# ADDIS Technical Architecture
## System Design and Implementation Documentation

**Author:** Shardae Douglas  
**Date:** September 2025  
**Version:** 1.0

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Components](#2-architecture-components)
3. [Data Flow Architecture](#3-data-flow-architecture)
4. [API Design](#4-api-design)
5. [Database Schema](#5-database-schema)
6. [Security Architecture](#6-security-architecture)
7. [Performance Optimization](#7-performance-optimization)
8. [Deployment Architecture](#8-deployment-architecture)

## 1. System Overview

### 1.1 High-Level Architecture

ADDIS follows a modular, microservices-inspired architecture with the following key principles:

- **Separation of Concerns:** Each component handles a specific responsibility
- **Loose Coupling:** Components communicate through well-defined interfaces
- **High Availability:** System designed for 99.9% uptime
- **Scalability:** Horizontal scaling capabilities
- **Maintainability:** Clean code architecture with comprehensive documentation

### 1.2 Technology Stack

**Backend:**
- **Language:** Python 3.13+
- **Framework:** Flask 3.1.3
- **Data Processing:** Pandas, NumPy
- **Machine Learning:** Scikit-learn
- **Visualization:** Matplotlib, Seaborn
- **HTTP Client:** Requests

**Frontend:**
- **HTML5:** Semantic markup
- **CSS3:** Bootstrap 5.3 framework
- **JavaScript:** ES6+ with async/await
- **Icons:** Font Awesome 6.0

**Data Sources:**
- **Primary:** NOAA NCEI CDO Web Services API
- **Secondary:** GHCN-Daily static files
- **Metadata:** GHCN station inventory

## 2. Architecture Components

### 2.1 Core Modules

#### 2.1.1 Dynamic Station Search (`dynamic_station_search.py`)
```python
class DynamicStationSearcher:
    """
    Handles real-time station searching and data fetching
    """
    def __init__(self):
        self.stations_df = None
        self.cache = {}
    
    def search_stations(self, query, country_code='US', limit=20):
        """Search stations by name, ID, or location"""
    
    def fetch_station_data_from_ncei(self, station_id, start_year=None, end_year=None):
        """Fetch weather data from NCEI API"""
```

**Responsibilities:**
- Station metadata management
- Real-time data fetching
- Caching and performance optimization
- Error handling and fallback mechanisms

#### 2.1.2 Comprehensive Anomaly Detector (`comprehensive_anomaly_detector.py`)
```python
class ComprehensiveAnomalyDetector:
    """
    Multi-element anomaly detection system
    """
    def __init__(self):
        self.weather_elements = {...}
        self.temperature_elements = [...]
        self.precipitation_elements = [...]
    
    def detect_comprehensive_anomalies(self, data, station_id, start_date, end_date, confidence_threshold):
        """Detect anomalies across all weather elements"""
```

**Responsibilities:**
- Multi-element anomaly detection
- Statistical analysis and baseline calculation
- Machine learning model integration
- Result interpretation and explanation generation

#### 2.1.3 GHCN Flag Handler (`ghcn_flag_handler.py`)
```python
class GHCNFlagHandler:
    """
    Processes GHCN-Daily quality control flags
    """
    def __init__(self):
        self.flag_descriptions = {...}
        self.quality_scores = {...}
    
    def parse_ghcn_attributes(self, attribute_string):
        """Parse mflag,qflag,sflag format"""
```

**Responsibilities:**
- GHCN flag parsing and interpretation
- Quality score calculation
- Data quality assessment
- Flag-based filtering and validation

#### 2.1.4 Station Downloader (`station_downloader.py`)
```python
class StationDownloader:
    """
    Manages station data downloading and processing
    """
    def __init__(self):
        self.ncei_base_url = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/"
    
    def download_station_data(self, station_id, start_year=None, end_year=None):
        """Download and process station data"""
```

**Responsibilities:**
- Batch station data downloading
- Data processing and validation
- File management and storage
- Progress tracking and error handling

### 2.2 Flask Application (`demo_app.py`)

#### 2.2.1 Application Structure
```python
app = Flask(__name__)
app.secret_key = 'addis-secret-key'

# Global data storage
weather_data = pd.DataFrame()

# Module initialization
station_downloader = StationDownloader()
dynamic_searcher = DynamicStationSearcher()
comprehensive_detector = ComprehensiveAnomalyDetector()
```

#### 2.2.2 Route Architecture
```python
# Core routes
@app.route('/')
def index():
    """Main application interface"""

# API routes
@app.route('/api/stations/search')
def search_stations_dynamic():
    """Dynamic station search endpoint"""

@app.route('/api/stations/<station_id>/fetch')
def fetch_station_data_dynamic(station_id):
    """Station data fetching endpoint"""

@app.route('/api/comprehensive-anomaly-detection', methods=['POST'])
def run_comprehensive_anomaly_detection():
    """Comprehensive anomaly detection endpoint"""
```

## 3. Data Flow Architecture

### 3.1 Data Flow Diagram

```
User Request → Web Interface → Flask App → Module Processing → NCEI API → Data Processing → Analysis → Results
     ↓              ↓            ↓            ↓              ↓           ↓              ↓         ↓
   Search      JavaScript    Route Handler  Station      HTTP Request  Pandas DF   ML Models   JSON
   Station      Functions     Functions     Searcher     Response      Processing   Analysis   Response
```

### 3.2 Detailed Data Flow

#### 3.2.1 Station Search Flow
1. **User Input:** Search query in web interface
2. **JavaScript:** `filterStations()` function
3. **API Call:** GET `/api/stations/search`
4. **Processing:** `DynamicStationSearcher.search_stations()`
5. **Response:** JSON list of matching stations
6. **Display:** Dynamic dropdown population

#### 3.2.2 Data Fetching Flow
1. **User Selection:** Station selection from dropdown
2. **JavaScript:** `loadStationData()` function
3. **API Call:** GET `/api/stations/<station_id>/fetch`
4. **Processing:** `DynamicStationSearcher.fetch_station_data_from_ncei()`
5. **NCEI Request:** HTTP GET to NCEI CDO API
6. **Data Processing:** Pandas DataFrame creation
7. **Response:** JSON station data summary
8. **Display:** Station information and data summary

#### 3.2.3 Anomaly Detection Flow
1. **User Request:** Analysis parameters (dates, confidence threshold)
2. **JavaScript:** `runAnomalyDetection()` function
3. **API Call:** POST `/api/comprehensive-anomaly-detection`
4. **Processing:** `ComprehensiveAnomalyDetector.detect_comprehensive_anomalies()`
5. **Baseline Calculation:** Statistical analysis for each element
6. **Anomaly Detection:** Z-score and ML model analysis
7. **Result Generation:** Comprehensive anomaly report
8. **Response:** JSON analysis results
9. **Display:** `displayComprehensiveResults()` function

## 4. API Design

### 4.1 RESTful API Principles

ADDIS follows RESTful API design principles:

- **Resource-Based URLs:** `/api/stations/{id}`
- **HTTP Methods:** GET, POST, PUT, DELETE as appropriate
- **Stateless:** Each request contains all necessary information
- **Cacheable:** Appropriate cache headers for performance
- **Uniform Interface:** Consistent response formats

### 4.2 API Endpoints

#### 4.2.1 Station Management
```http
GET /api/stations/search?q={query}&country={country}&limit={limit}
POST /api/stations/download
GET /api/stations/load-existing
GET /api/stations/{station_id}/fetch
GET /api/stations/search-and-fetch?q={query}&country={country}
```

#### 4.2.2 Analysis Endpoints
```http
POST /api/comprehensive-anomaly-detection
GET /api/station/{station_id}/data
GET /api/station/{station_id}/ghcn-flags
```

#### 4.2.3 Response Format
```json
{
  "summary": {
    "station_id": "USC00086700",
    "analysis_period": "2023-01-01 to 2023-12-31",
    "total_records": 365,
    "total_anomalies": 12,
    "elements_analyzed": ["TMAX_F", "TMIN_F", "PRCP_IN"],
    "confidence_threshold": 1.0
  },
  "element_summaries": {
    "TMAX_F": {
      "total_records": 365,
      "anomalies_detected": 5,
      "mean": 75.2,
      "std": 12.4
    }
  },
  "anomalies": {
    "comprehensive": {
      "anomalies": [...],
      "total": 12
    }
  }
}
```

### 4.3 Error Handling

#### 4.3.1 HTTP Status Codes
- **200 OK:** Successful request
- **400 Bad Request:** Invalid parameters
- **404 Not Found:** Resource not found
- **500 Internal Server Error:** Server error

#### 4.3.2 Error Response Format
```json
{
  "error": "Error message description",
  "error_code": "ERROR_CODE",
  "details": "Additional error details",
  "timestamp": "2025-09-30T10:30:00Z"
}
```

## 5. Database Schema

### 5.1 Data Storage Architecture

ADDIS uses a hybrid storage approach:

#### 5.1.1 In-Memory Storage
```python
# Global data storage
weather_data = pd.DataFrame()

# Cache storage
station_cache = {}
analysis_cache = {}
```

#### 5.1.2 File-Based Storage
```
Datasets/
├── GHCN_Data/
│   ├── ghcnd-stations.txt          # Station metadata
│   ├── Training_Data/
│   │   └── ghcn_cleaned.csv        # Demo data
│   └── Downloaded_Stations/        # User-downloaded data
│       ├── USC00086700.csv
│       └── US1MOTX0008.csv
```

### 5.2 Data Models

#### 5.2.1 Station Model
```python
class Station:
    id: str                    # Station ID (e.g., "USC00086700")
    name: str                  # Station name
    latitude: float            # Latitude in decimal degrees
    longitude: float           # Longitude in decimal degrees
    elevation: float           # Elevation in meters
    country: str               # Country code
    state: str                 # State/province
    first_year: int            # First year of data
    last_year: int             # Last year of data
    elements: List[str]        # Available weather elements
```

#### 5.2.2 Weather Data Model
```python
class WeatherRecord:
    station_id: str            # Station identifier
    date: datetime             # Date of observation
    elements: Dict[str, float] # Weather element values
    attributes: Dict[str, str] # GHCN quality flags
    quality_scores: Dict[str, float] # Quality scores
```

#### 5.2.3 Anomaly Model
```python
class Anomaly:
    date: datetime             # Date of anomaly
    station_id: str            # Station identifier
    element: str                # Weather element
    value: float               # Observed value
    z_score: float             # Statistical Z-score
    anomaly_type: str          # "High" or "Low"
    severity: str              # "mild", "moderate", "extreme"
    explanation: str           # Human-readable explanation
    baseline: Dict             # Baseline statistics
```

## 6. Security Architecture

### 6.1 Security Principles

- **Input Validation:** All user inputs are validated and sanitized
- **SQL Injection Prevention:** Parameterized queries and input validation
- **XSS Protection:** Output encoding and CSP headers
- **CSRF Protection:** Token-based request validation
- **Rate Limiting:** API request throttling

### 6.2 Authentication and Authorization

#### 6.2.1 Current Implementation
```python
app.secret_key = 'addis-secret-key'  # Session management
```

#### 6.2.2 Future Enhancements
- **API Key Authentication:** For external API access
- **User Role Management:** Admin, researcher, public user roles
- **Audit Logging:** Track all system access and modifications

### 6.3 Data Privacy

- **No Personal Data:** System only processes weather data
- **Data Retention:** Configurable data retention policies
- **Access Logging:** Track data access patterns
- **Encryption:** HTTPS for all data transmission

## 7. Performance Optimization

### 7.1 Caching Strategy

#### 7.1.1 Multi-Level Caching
```python
# Level 1: In-memory cache
station_cache = {}

# Level 2: File-based cache
cache_dir = "cache/"

# Level 3: NCEI API caching
# Respects HTTP cache headers
```

#### 7.1.2 Cache Invalidation
- **Time-based:** Cache expires after 24 hours
- **Event-based:** Cache invalidated on data updates
- **Manual:** Admin can clear cache

### 7.2 Database Optimization

#### 7.2.1 Indexing Strategy
```python
# Pandas DataFrame optimization
df.set_index(['STATION', 'DATE'], inplace=True)
df.sort_index(inplace=True)
```

#### 7.2.2 Query Optimization
- **Selective Loading:** Load only required data
- **Batch Processing:** Process multiple stations together
- **Lazy Loading:** Load data on demand

### 7.3 API Performance

#### 7.3.1 Response Optimization
- **JSON Compression:** Gzip compression for large responses
- **Pagination:** Large result sets paginated
- **Field Selection:** Allow clients to request specific fields

#### 7.3.2 Concurrent Processing
```python
# Async processing for multiple stations
import asyncio
import aiohttp

async def fetch_multiple_stations(station_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_station_data(session, sid) for sid in station_ids]
        return await asyncio.gather(*tasks)
```

## 8. Deployment Architecture

### 8.1 Development Environment

#### 8.1.1 Local Development
```bash
# Development server
python demo_app.py

# Environment setup
conda create -n addis python=3.13
conda activate addis
pip install -r requirements.txt
```

#### 8.1.2 Development Tools
- **Code Quality:** Black, Flake8, Pylint
- **Testing:** Pytest, Coverage
- **Documentation:** Sphinx, MkDocs
- **Version Control:** Git with GitHub

### 8.2 Production Deployment

#### 8.2.1 Containerization
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5001

CMD ["python", "demo_app.py"]
```

#### 8.2.2 Production Considerations
- **WSGI Server:** Gunicorn or uWSGI
- **Reverse Proxy:** Nginx
- **Process Management:** Systemd or Docker Compose
- **Monitoring:** Application performance monitoring
- **Logging:** Centralized logging system

### 8.3 Scalability Architecture

#### 8.3.1 Horizontal Scaling
- **Load Balancer:** Distribute requests across multiple instances
- **Stateless Design:** No server-side session storage
- **Shared Cache:** Redis for distributed caching

#### 8.3.2 Vertical Scaling
- **Resource Monitoring:** CPU, memory, disk usage
- **Auto-scaling:** Dynamic resource allocation
- **Performance Tuning:** Database and application optimization

---

**Document Classification:** Technical Architecture  
**Review Status:** Draft  
**Next Review Date:** December 2025
