# GHCN-D Weather Data Anomaly Detection System

A comprehensive AI-powered anomaly detection system for GHCN-D weather data from NOAA. This system can identify unusual weather patterns, extreme temperatures, precipitation anomalies, and seasonal deviations.

## 🎯 Features

### Multiple Detection Methods
- **Statistical Methods**: Z-score based anomaly detection
- **Machine Learning Models**:
  - Isolation Forest (ensemble-based)
  - Local Outlier Factor (density-based)
  - One-Class SVM (support vector-based)

### Comprehensive Analysis
- Temperature anomaly detection (extreme highs/lows)
- Precipitation anomaly detection (drought/flood events)
- Seasonal pattern analysis
- Multi-dimensional feature engineering
- Real-time detection capabilities

### Visualization & Reporting
- Interactive plots with Plotly
- Comprehensive statistical summaries
- Model comparison dashboards
- Export capabilities for further analysis

## 📁 Project Structure

```
├── Notebooks/
│   ├── AnomalyDetection.ipynb     # Main anomaly detection notebook
│   ├── ghcn_cleaning.ipynb       # Data cleaning
│   └── TrainingPrep.ipynb        # Initial training
├── Datasets/
│   └── GHCN_Data/
│       ├── Raw_Data/              # Original GHCN data
│       └── Training_Data/         # Cleaned data + anomaly results
├── weather_anomaly_detector.py    # Production-ready detector class
├── requirements_anomaly.txt        # Additional dependencies
└── README.md                      # This file
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Install additional dependencies
pip install -r requirements_anomaly.txt

# Or install individually:
pip install plotly scikit-learn scipy
```

### 2. Run the Analysis
```bash
# Open and run the main notebook
jupyter notebook Notebooks/AnomalyDetection.ipynb

# Or use the production script
python weather_anomaly_detector.py
```

### 3. Using the Detector Class
```python
from weather_anomaly_detector import WeatherAnomalyDetector

# Initialize detector
detector = WeatherAnomalyDetector()

# Load your data
df = pd.read_csv('your_weather_data.csv')

# Train models
detector.train_models(df)

# Detect anomalies
anomalies = detector.detect_anomalies(df)

# Save models for future use
detector.save_models('models/')
```

## 🔧 Technical Details

### Feature Engineering
The system creates sophisticated features for better anomaly detection:

- **Temporal Features**: Year, month, day, day-of-year, season
- **Temperature Features**: Max/min temperatures, temperature range
- **Precipitation Features**: Daily precipitation, 7-day rolling sums
- **Seasonal Deviations**: Deviations from monthly averages
- **Rolling Averages**: 7-day moving averages for trend analysis

### Model Parameters
- **Isolation Forest**: `contamination=0.1`, `random_state=42`
- **Local Outlier Factor**: `n_neighbors=20`, `contamination=0.1`
- **One-Class SVM**: `nu=0.1`, `kernel='rbf'`, `gamma='scale'`
- **Z-Score Threshold**: `threshold=3` (3 standard deviations)

### Data Preprocessing
- Temperature conversion (tenths of °C → °C)
- Precipitation conversion (tenths of mm → mm)
- Missing value handling
- Feature standardization
- Temporal feature extraction

## 📊 Output Files

The system generates several output files:

- `anomalies_isolation_forest.csv` - Isolation Forest results
- `anomalies_local_outlier_factor.csv` - LOF results
- `anomalies_one-class_svm.csv` - One-Class SVM results
- `anomalies_statistical.csv` - Statistical method results
- `model_comparison.csv` - Model performance comparison

## 🎨 Visualization Features

### Interactive Dashboards
- Temperature and precipitation time series with anomaly markers
- Distribution plots for understanding data patterns
- Seasonal pattern analysis
- Model comparison charts
- Statistical summaries

### Customizable Plots
- Multiple color schemes
- Hover information
- Zoom and pan capabilities
- Export to various formats

## 🔍 Anomaly Types Detected

### Temperature Anomalies
- **Extreme Heat**: Unusually high maximum temperatures
- **Extreme Cold**: Unusually low minimum temperatures
- **Temperature Swings**: Unusual daily temperature ranges
- **Seasonal Deviations**: Temperatures outside normal seasonal ranges

### Precipitation Anomalies
- **Heavy Rainfall**: Extreme precipitation events
- **Drought Conditions**: Extended periods of no precipitation
- **Precipitation Patterns**: Unusual precipitation timing or amounts

### Pattern Anomalies
- **Seasonal Shifts**: Unusual seasonal patterns
- **Trend Deviations**: Departures from normal weather trends
- **Multi-variate Anomalies**: Complex patterns across multiple variables

## 📈 Model Performance

### Isolation Forest
- **Best for**: General anomaly detection
- **Strengths**: Handles high-dimensional data well, robust to outliers
- **Use case**: Overall weather pattern anomalies

### Local Outlier Factor
- **Best for**: Local density-based anomalies
- **Strengths**: Good at detecting local patterns, handles clusters
- **Use case**: Regional weather pattern deviations

### One-Class SVM
- **Best for**: Extreme weather events
- **Strengths**: Good boundary definition, handles non-linear patterns
- **Use case**: Severe weather event detection

### Statistical Methods
- **Best for**: Simple threshold-based detection
- **Strengths**: Interpretable, fast computation
- **Use case**: Quick screening for extreme values

## 🛠️ Customization

### Adjusting Sensitivity
```python
# Modify contamination rate (lower = more sensitive)
iso_forest = IsolationForest(contamination=0.05)  # More sensitive
iso_forest = IsolationForest(contamination=0.2)   # Less sensitive

# Adjust Z-score threshold
anomalies = detector.detect_statistical_anomalies(df, threshold=2.5)  # More sensitive
anomalies = detector.detect_statistical_anomalies(df, threshold=4.0)   # Less sensitive
```

### Adding New Features
```python
# Extend feature engineering
def custom_preprocess(df):
    df = preprocess_weather_data(df)
    # Add your custom features
    df['CUSTOM_FEATURE'] = df['TMAX_C'] * df['PRCP_MM']
    return df
```

## 🔬 Research Applications

This system is suitable for:
- **Climate Research**: Identifying unusual weather patterns
- **Meteorological Studies**: Analyzing weather station data quality
- **Agricultural Applications**: Detecting weather anomalies affecting crops
- **Environmental Monitoring**: Tracking climate change indicators
- **Data Quality Assurance**: Identifying potential data errors

## 📚 References

- [GHCN-D Dataset Documentation](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily)
- [Scikit-learn Anomaly Detection](https://scikit-learn.org/stable/modules/outlier_detection.html)
- [Isolation Forest Paper](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf)

## 🤝 Contributing

Feel free to contribute by:
- Adding new anomaly detection algorithms
- Improving feature engineering
- Enhancing visualization capabilities
- Adding more evaluation metrics
- Optimizing performance

## 📄 License

This project is part of the ADDIS weather analysis system. Please refer to the main project license.

---

**Note**: This anomaly detection system is designed for research and analysis purposes. For operational weather forecasting, please consult with meteorological experts and use appropriate validation procedures.
