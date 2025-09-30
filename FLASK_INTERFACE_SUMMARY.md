# Flask Web Interface for US Weather Anomaly Detection

## 🎯 **Overview**

### **1. Full-Featured Flask Application** (`app.py`)
- **Complete API**: RESTful endpoints for station data and anomaly detection
- **Advanced Detection**: Integration with enhanced anomaly detection system
- **Report Generation**: Comprehensive anomaly reports with visualizations
- **Export Functionality**: Download reports as JSON files

### **2. Demo Application** (`demo_app.py`)
- **Simplified Version**: Works with existing data without additional setup
- **Statistical Detection**: Z-score based anomaly detection
- **Basic Visualizations**: Temperature and precipitation charts
- **Easy Testing**: Ready to run with your current dataset

### **3. Interactive Web Interface** (`templates/`)
- **Modern UI**: Bootstrap-based responsive design
- **Station Selection**: Dropdown with available US stations
- **Date Range Picker**: Interactive date selection
- **Real-time Results**: Live anomaly detection and visualization
- **Export Options**: Download comprehensive reports

### **4. Supporting Files**
- `launch_app.py` - Application launcher with dependency checking
- `test_flask_app.py` - API testing script
- `requirements_flask.txt` - Python dependencies
- `FLASK_APP_README.md` - Comprehensive documentation

## 🌐 **How to Use**

### **Quick Start (Demo Version)**
```bash
# Run the demo application
python demo_app.py

# Open your browser to:
# http://localhost:5001
```

### **Full Version (Requires US Station Data)**
```bash
# First, generate US station data
python run_us_filter.py

# Then run the full application
python app.py

# Open your browser to:
# http://localhost:5000
```

## 🎮 **Interface Features**

### **Station Selection**
- **Dropdown Menu**: Choose from available US weather stations
- **Station Details**: View location, coordinates, and data coverage
- **Automatic Date Range**: Data availability automatically populated

### **Analysis Configuration**
- **Date Range**: Select start and end dates for analysis
- **Sensitivity Levels**: Adjustable confidence thresholds (0.3-0.9)
- **Detection Methods**: Choose statistical, ML, or both approaches
- **Real-time Validation**: Input validation and error handling

### **Anomaly Detection**
- **One-Click Analysis**: Run detection with a single button click
- **Progress Indicators**: Loading spinners and status updates
- **Multiple Algorithms**: Statistical (Z-score) and ML (Isolation Forest, LOF, One-Class SVM)
- **Comprehensive Results**: Detailed anomaly information

### **Results Display**
- **Summary Cards**: Total anomalies, data quality, analysis period
- **Interactive Charts**: Temperature and precipitation timelines with anomaly highlights
- **Anomaly Details**: Specific information for each detected anomaly
- **Export Options**: Download reports as JSON files

## 📊 **API Endpoints**

### **GET /api/stations**
Returns list of available US stations with metadata.

### **GET /api/station/{station_id}/data**
Returns weather data and summary for a specific station.

### **POST /api/anomaly-detection**
Runs anomaly detection with specified parameters:
```json
{
  "station_id": "USC00086700",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "confidence_threshold": 0.5,
  "methods": ["statistical", "ml"]
}
```

### **POST /api/export-report**
Exports anomaly report as downloadable JSON file.

## 🔍 **Anomaly Detection Methods**

### **Statistical Methods**
- **Z-Score Analysis**: Detects values beyond statistical thresholds
- **Percentile Analysis**: Identifies extreme precipitation events
- **Temporal Consistency**: Checks for unusual day-to-day changes

### **Machine Learning Methods**
- **Isolation Forest**: Identifies outliers in high-dimensional space
- **Local Outlier Factor**: Detects local density-based anomalies
- **One-Class SVM**: Learns normal patterns and flags deviations

### **Quality Assurance Integration**
- **Data Quality Scoring**: Assesses data reliability
- **QA Flag Integration**: Incorporates GHCN-Daily quality flags
- **Confidence Metrics**: Provides reliability scores for detections

## 📈 **Visualizations**

### **Temperature Timeline**
- **Line Charts**: Maximum and minimum temperature trends
- **Anomaly Markers**: Red X markers highlight detected anomalies
- **Interactive Elements**: Hover tooltips and zoom capabilities

### **Precipitation Timeline**
- **Bar Charts**: Daily precipitation amounts
- **Anomaly Highlights**: Extreme precipitation events marked
- **Seasonal Patterns**: Visual identification of seasonal anomalies

### **Anomaly Summary**
- **Comparative Charts**: Side-by-side comparison of detection methods
- **Count Visualization**: Bar charts showing anomaly counts by method
- **Confidence Levels**: Visual representation of detection confidence

## 🎯 **Example Usage Workflow**

### **Step 1: Select Station**
1. Open the web interface
2. Choose a US weather station from the dropdown
3. View station details and data coverage

### **Step 2: Configure Analysis**
1. Select date range for analysis
2. Choose sensitivity level (confidence threshold)
3. Select detection methods (statistical, ML, or both)

### **Step 3: Run Detection**
1. Click "Run Anomaly Detection"
2. Wait for processing (typically 10-30 seconds)
3. View real-time progress indicators

### **Step 4: Review Results**
1. Examine summary statistics
2. Analyze visualizations
3. Review detailed anomaly information
4. Export report if needed

## 🔧 **Technical Features**

### **Backend Architecture**
- **Flask Framework**: Lightweight and flexible web framework
- **RESTful API**: Clean, stateless API design
- **Error Handling**: Comprehensive error management
- **Logging**: Detailed logging for debugging and monitoring

### **Frontend Technology**
- **Bootstrap 5**: Modern, responsive UI framework
- **JavaScript**: Interactive client-side functionality
- **AJAX**: Asynchronous data loading and updates
- **Chart.js**: Dynamic data visualization

### **Data Processing**
- **Pandas Integration**: Efficient data manipulation
- **NumPy**: Numerical computations
- **Matplotlib/Seaborn**: Statistical visualizations
- **Base64 Encoding**: Image data transmission

## 📁 **File Structure**

```
├── app.py                              # Full-featured Flask application
├── demo_app.py                         # Simplified demo application
├── launch_app.py                       # Application launcher
├── test_flask_app.py                   # API testing script
├── templates/
│   ├── index.html                      # Full-featured web interface
│   └── demo_index.html                 # Simplified demo interface
├── requirements_flask.txt              # Python dependencies
├── FLASK_APP_README.md                 # Comprehensive documentation
└── README.md                           # This summary
```

## 🚀 **Getting Started**

### **Option 1: Demo Version (Recommended for Testing)**
```bash
# Run the demo with existing data
python demo_app.py

# Access at: http://localhost:5001
```

### **Option 2: Full Version**
```bash
# Generate US station data first
python run_us_filter.py

# Run the full application
python app.py

# Access at: http://localhost:5000
```

### **Option 3: Using Launcher**
```bash
# Use the launcher script
python launch_app.py
```

## 🎉 **Key Benefits**

### **User-Friendly Interface**
- **No Coding Required**: Point-and-click anomaly detection
- **Real-time Results**: Immediate feedback and visualizations
- **Export Capabilities**: Download reports for further analysis

### **Comprehensive Analysis**
- **Multiple Methods**: Statistical and machine learning approaches
- **Quality Integration**: QA-aware anomaly detection
- **Detailed Reports**: Comprehensive anomaly information

### **Scalable Architecture**
- **API-First Design**: Easy integration with other systems
- **Modular Structure**: Easy to extend and customize
- **Production Ready**: Suitable for deployment

## 🔮 **Future Enhancements**

### **Planned Features**
- **Real-time Data Updates**: Live data integration
- **Multi-station Analysis**: Compare anomalies across stations
- **Advanced Visualizations**: Interactive maps and 3D charts
- **Machine Learning Training**: Custom model training interface

### **Integration Opportunities**
- **Database Integration**: Store results in database
- **External APIs**: Weather alert integration
- **Mobile App**: Native mobile application
- **Cloud Deployment**: AWS/Azure deployment options

## 📞 **Support and Troubleshooting**

### **Common Issues**
1. **Port Conflicts**: Change port in app.py if 5000/5001 is occupied
2. **Missing Data**: Run `python run_us_filter.py` to generate station data
3. **Import Errors**: Install requirements with `pip install -r requirements_flask.txt`
4. **Browser Issues**: Clear cache and try different browser

### **Getting Help**
- Check the `FLASK_APP_README.md` for detailed documentation
- Review error messages in the terminal output
- Test API endpoints with `python test_flask_app.py`

## 🎯 **Summary**

The Flask web interface provides a complete solution for interactive weather anomaly detection:

✅ **Easy to Use**: Point-and-click interface for non-technical users  
✅ **Comprehensive**: Multiple detection methods and detailed analysis  
✅ **Visual**: Interactive charts and real-time visualizations  
✅ **Exportable**: Download reports for further analysis  
✅ **Scalable**: API-first design for integration and extension  

**Ready to use**: Run `python demo_app.py` and open `http://localhost:5001` to start 
