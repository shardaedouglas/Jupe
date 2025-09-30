#!/usr/bin/env python3
"""
Enhanced GHCN-D Weather Data Anomaly Detection System
Incorporating proven QA methodologies from GHCN-Daily processing

Based on: Menne et al. (2012) - "An Overview of the Global Historical Climatology Network-Daily Database"
Author: Shardae Douglas
Date: 2025
"""

import pandas as pd
import numpy as np
import pickle
import joblib
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from scipy.stats import zscore
from scipy.spatial.distance import cdist
import warnings
warnings.filterwarnings('ignore')

class EnhancedWeatherAnomalyDetector:
    """
    Enhanced anomaly detection system incorporating GHCN-Daily QA methodologies
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the enhanced anomaly detector
        """
        self.models = {}
        self.scaler = None
        self.feature_columns = None
        self.is_trained = False
        self.qa_results = {}
        self.neighbor_stations = {}
        
        if model_path:
            self.load_models(model_path)
    
    def format_checking(self, df):
        """
        GHCN-Daily Format Checking Program
        Identifies basic data format violations
        """
        format_issues = []
        
        # Check for invalid dates
        try:
            pd.to_datetime(df['DATE'], format='%m-%d-%Y')
        except:
            format_issues.append("Invalid date format")
        
        # Check for invalid temperature values
        temp_cols = ['TMAX', 'TMIN']
        for col in temp_cols:
            if col in df.columns:
                invalid_temps = df[df[col].notna() & ((df[col] < -999) | (df[col] > 999))]
                if len(invalid_temps) > 0:
                    format_issues.append(f"Invalid temperature values in {col}")
        
        # Check for invalid precipitation values
        if 'PRCP' in df.columns:
            invalid_prcp = df[df['PRCP'].notna() & (df['PRCP'] < 0)]
            if len(invalid_prcp) > 0:
                format_issues.append("Negative precipitation values")
        
        # Check for missing station metadata
        required_meta = ['STATION', 'LATITUDE', 'LONGITUDE', 'NAME']
        for col in required_meta:
            if col not in df.columns or df[col].isna().all():
                format_issues.append(f"Missing {col} metadata")
        
        return format_issues
    
    def physical_limits_check(self, df):
        """
        Physical and Absolute Limits Check
        Based on GHCN-Daily QA methodology
        """
        limits_issues = []
        
        # Temperature limits (in tenths of degrees Celsius)
        temp_limits = {
            'TMAX': (-999, 600),  # -99.9°C to 60.0°C
            'TMIN': (-999, 500)   # -99.9°C to 50.0°C
        }
        
        for col, (min_val, max_val) in temp_limits.items():
            if col in df.columns:
                violations = df[df[col].notna() & ((df[col] < min_val) | (df[col] > max_val))]
                if len(violations) > 0:
                    limits_issues.append(f"{col} values outside physical limits: {len(violations)} violations")
        
        # Precipitation limits (in tenths of mm)
        if 'PRCP' in df.columns:
            prcp_violations = df[df['PRCP'].notna() & (df['PRCP'] > 2000)]  # > 200mm/day
            if len(prcp_violations) > 0:
                limits_issues.append(f"Precipitation values exceed reasonable limits: {len(prcp_violations)} violations")
        
        return limits_issues
    
    def climatological_limits_check(self, df):
        """
        Climatological Limits Check
        Station-specific climatological bounds
        """
        climatological_issues = []
        
        # Convert to Fahrenheit for analysis
        df_temp = df.copy()
        df_temp['TMAX_F'] = df_temp['TMAX'] / 10.0 * 9/5 + 32
        df_temp['TMIN_F'] = df_temp['TMIN'] / 10.0 * 9/5 + 32
        
        # Calculate climatological bounds (95th and 5th percentiles)
        for col in ['TMAX_F', 'TMIN_F']:
            if col in df_temp.columns:
                data = df_temp[col].dropna()
                if len(data) > 30:  # Need sufficient data
                    p95 = np.percentile(data, 95)
                    p5 = np.percentile(data, 5)
                    
                    # Flag values beyond 3 standard deviations from climatological mean
                    mean_val = data.mean()
                    std_val = data.std()
                    extreme_values = df_temp[
                        df_temp[col].notna() & 
                        (np.abs(df_temp[col] - mean_val) > 3 * std_val)
                    ]
                    
                    if len(extreme_values) > 0:
                        climatological_issues.append(f"{col} climatological extremes: {len(extreme_values)} values")
        
        return climatological_issues
    
    def temporal_persistence_check(self, df):
        """
        Temporal Persistence Check
        Identifies excessive persistence in values
        """
        persistence_issues = []
        
        # Check for excessive persistence in temperature
        for col in ['TMAX', 'TMIN']:
            if col in df.columns:
                data = df[col].dropna()
                if len(data) > 10:
                    # Count consecutive identical values
                    consecutive_counts = []
                    current_count = 1
                    
                    for i in range(1, len(data)):
                        if data.iloc[i] == data.iloc[i-1]:
                            current_count += 1
                        else:
                            consecutive_counts.append(current_count)
                            current_count = 1
                    consecutive_counts.append(current_count)
                    
                    max_consecutive = max(consecutive_counts)
                    if max_consecutive > 7:  # More than 7 consecutive identical values
                        persistence_issues.append(f"{col} excessive persistence: {max_consecutive} consecutive identical values")
        
        return persistence_issues
    
    def internal_consistency_check(self, df):
        """
        Internal Consistency Check
        Checks for logical inconsistencies between elements
        """
        consistency_issues = []
        
        # Convert temperatures for consistency check
        df_temp = df.copy()
        df_temp['TMAX_C'] = df_temp['TMAX'] / 10.0
        df_temp['TMIN_C'] = df_temp['TMIN'] / 10.0
        
        # Check TMAX >= TMIN
        if 'TMAX_C' in df_temp.columns and 'TMIN_C' in df_temp.columns:
            inconsistent = df_temp[
                df_temp['TMAX_C'].notna() & 
                df_temp['TMIN_C'].notna() & 
                (df_temp['TMAX_C'] < df_temp['TMIN_C'])
            ]
            
            if len(inconsistent) > 0:
                consistency_issues.append(f"TMAX < TMIN inconsistency: {len(inconsistent)} cases")
        
        # Check temperature range reasonableness
        df_temp['TEMP_RANGE'] = df_temp['TMAX_C'] - df_temp['TMIN_C']
        extreme_ranges = df_temp[
            df_temp['TEMP_RANGE'].notna() & 
            (df_temp['TEMP_RANGE'] > 50)  # > 50°C daily range
        ]
        
        if len(extreme_ranges) > 0:
            consistency_issues.append(f"Extreme temperature ranges: {len(extreme_ranges)} cases")
        
        return consistency_issues
    
    def neighbor_station_check(self, df, neighbor_data=None):
        """
        Neighbor Station Comparison Check
        Based on GHCN-Daily methodology for spatial validation
        """
        neighbor_issues = []
        
        if neighbor_data is None:
            return neighbor_issues
        
        # Convert temperatures to Fahrenheit
        df_temp = df.copy()
        df_temp['TMAX_F'] = df_temp['TMAX'] / 10.0 * 9/5 + 32
        df_temp['TMIN_F'] = df_temp['TMIN'] / 10.0 * 9/5 + 32
        
        # Get station coordinates
        if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns:
            station_lat = df['LATITUDE'].iloc[0]
            station_lon = df['LONGITUDE'].iloc[0]
            
            # Find nearby stations (within 75km as per GHCN-Daily)
            neighbor_coords = neighbor_data[['LATITUDE', 'LONGITUDE']].values
            distances = cdist([[station_lat, station_lon]], neighbor_coords)[0]
            nearby_stations = neighbor_data[distances < 0.675]  # ~75km in degrees
            
            if len(nearby_stations) > 0:
                # Compare temperature patterns
                for col in ['TMAX_F', 'TMIN_F']:
                    if col in df_temp.columns:
                        station_data = df_temp[col].dropna()
                        if len(station_data) > 30:
                            # Calculate correlation with nearby stations
                            correlations = []
                            for _, neighbor in nearby_stations.iterrows():
                                neighbor_data_col = neighbor_data[neighbor_data['STATION'] == neighbor['STATION']]
                                if len(neighbor_data_col) > 0 and col in neighbor_data_col.columns:
                                    neighbor_vals = neighbor_data_col[col].dropna()
                                    if len(neighbor_vals) > 10:
                                        # Align dates for comparison
                                        common_dates = set(station_data.index) & set(neighbor_vals.index)
                                        if len(common_dates) > 10:
                                            corr = np.corrcoef(
                                                station_data.loc[list(common_dates)],
                                                neighbor_vals.loc[list(common_dates)]
                                            )[0, 1]
                                            if not np.isnan(corr):
                                                correlations.append(corr)
                            
                            if len(correlations) > 0:
                                avg_correlation = np.mean(correlations)
                                if avg_correlation < 0.3:  # Low correlation with neighbors
                                    neighbor_issues.append(f"{col} low correlation with neighbors: {avg_correlation:.3f}")
        
        return neighbor_issues
    
    def comprehensive_qa_check(self, df, neighbor_data=None):
        """
        Comprehensive QA Check incorporating all GHCN-Daily methodologies
        """
        qa_results = {
            'format_issues': self.format_checking(df),
            'physical_limits': self.physical_limits_check(df),
            'climatological_limits': self.climatological_limits_check(df),
            'temporal_persistence': self.temporal_persistence_check(df),
            'internal_consistency': self.internal_consistency_check(df),
            'neighbor_comparison': self.neighbor_station_check(df, neighbor_data)
        }
        
        # Calculate overall QA score
        total_issues = sum(len(issues) for issues in qa_results.values())
        qa_results['total_issues'] = total_issues
        qa_results['qa_score'] = max(0, 100 - total_issues * 10)  # Penalty system
        
        return qa_results
    
    def preprocess_data(self, df):
        """
        Enhanced preprocessing with QA integration
        """
        data = df.copy()
        
        # Run comprehensive QA check
        qa_results = self.comprehensive_qa_check(data)
        self.qa_results = qa_results
        
        # Log QA issues
        if qa_results['total_issues'] > 0:
            print(f"QA Issues Detected: {qa_results['total_issues']} total issues")
            for category, issues in qa_results.items():
                if isinstance(issues, list) and len(issues) > 0:
                    print(f"  {category}: {len(issues)} issues")
        
        # Convert DATE to datetime
        data['DATE'] = pd.to_datetime(data['DATE'], format='%m-%d-%Y')
        
        # Extract temporal features
        data['YEAR'] = data['DATE'].dt.year
        data['MONTH'] = data['DATE'].dt.month
        data['DAY'] = data['DATE'].dt.day
        data['DAY_OF_YEAR'] = data['DATE'].dt.dayofyear
        
        # Convert temperature from tenths of degrees Celsius to Celsius, then to Fahrenheit
        data['TMAX_C'] = data['TMAX'] / 10.0
        data['TMIN_C'] = data['TMIN'] / 10.0
        data['TMAX_F'] = (data['TMAX_C'] * 9/5) + 32
        data['TMIN_F'] = (data['TMIN_C'] * 9/5) + 32
        
        # Calculate temperature range in both Celsius and Fahrenheit
        data['TEMP_RANGE_C'] = data['TMAX_C'] - data['TMIN_C']
        data['TEMP_RANGE_F'] = data['TMAX_F'] - data['TMIN_F']
        
        # Convert precipitation from tenths of mm to mm, then to inches
        data['PRCP_MM'] = data['PRCP'] / 10.0
        data['PRCP_IN'] = data['PRCP_MM'] / 25.4
        
        # Handle missing values
        data['PRCP_MM'] = data['PRCP_MM'].fillna(0)
        data['PRCP_IN'] = data['PRCP_IN'].fillna(0)
        
        # Create rolling averages for trend analysis (using Fahrenheit and inches)
        data['TMAX_7DAY_AVG_F'] = data['TMAX_F'].rolling(window=7, min_periods=1).mean()
        data['TMIN_7DAY_AVG_F'] = data['TMIN_F'].rolling(window=7, min_periods=1).mean()
        data['PRCP_7DAY_SUM_IN'] = data['PRCP_IN'].rolling(window=7, min_periods=1).sum()
        
        # Calculate deviations from seasonal averages (using Fahrenheit and inches)
        seasonal_avg_f = data.groupby(['MONTH'])['TMAX_F'].mean()
        data['TMAX_SEASONAL_DEV_F'] = data['TMAX_F'] - data['MONTH'].map(seasonal_avg_f)
        
        seasonal_avg_min_f = data.groupby(['MONTH'])['TMIN_F'].mean()
        data['TMIN_SEASONAL_DEV_F'] = data['TMIN_F'] - data['MONTH'].map(seasonal_avg_min_f)
        
        seasonal_avg_prcp_in = data.groupby(['MONTH'])['PRCP_IN'].mean()
        data['PRCP_SEASONAL_DEV_IN'] = data['PRCP_IN'] - data['MONTH'].map(seasonal_avg_prcp_in)
        
        # Add QA-based features
        data['QA_SCORE'] = qa_results['qa_score']
        data['HAS_QA_ISSUES'] = qa_results['total_issues'] > 0
        
        return data
    
    def prepare_features(self, df):
        """
        Enhanced feature preparation with QA integration
        """
        if self.feature_columns is None:
            self.feature_columns = ['TMAX_F', 'TMIN_F', 'PRCP_IN', 'TEMP_RANGE_F', 
                                  'TMAX_7DAY_AVG_F', 'TMIN_7DAY_AVG_F', 'PRCP_7DAY_SUM_IN',
                                  'TMAX_SEASONAL_DEV_F', 'TMIN_SEASONAL_DEV_F', 'PRCP_SEASONAL_DEV_IN',
                                  'MONTH', 'DAY_OF_YEAR', 'QA_SCORE']
        
        # Check which features are available and create missing ones
        available_features = []
        for feature in self.feature_columns:
            if feature in df.columns:
                available_features.append(feature)
            else:
                # Create missing features with default values
                if feature == 'QA_SCORE':
                    df[feature] = 100  # Default high QA score
                    available_features.append(feature)
                else:
                    print(f"Warning: Feature '{feature}' not found in dataframe")
        
        X = df[available_features].copy()
        X = X.fillna(X.mean())
        
        return X
    
    def train_models(self, df, optimize=True):
        """
        Train enhanced anomaly detection models
        
        Args:
            df (pd.DataFrame): Processed weather data
            optimize (bool): Whether to optimize model parameters based on QA results
        """
        # Ensure data is preprocessed first
        if 'QA_SCORE' not in df.columns:
            print("Preprocessing data with QA integration...")
            df = self.preprocess_data(df)
        
        # Prepare features
        X = self.prepare_features(df)
        
        # Standardize features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models with enhanced parameters based on QA results
        contamination_rate = 0.1
        if optimize and self.qa_results['total_issues'] > 5:
            contamination_rate = 0.15  # Higher contamination for stations with QA issues
        
        # Isolation Forest
        self.models['Isolation Forest'] = IsolationForest(
            contamination=contamination_rate, 
            random_state=42,
            n_estimators=200  # More trees for better performance
        )
        self.models['Isolation Forest'].fit(X_scaled)
        
        # Local Outlier Factor
        self.models['Local Outlier Factor'] = LocalOutlierFactor(
            n_neighbors=20, 
            contamination=contamination_rate
        )
        
        # One-Class SVM
        self.models['One-Class SVM'] = OneClassSVM(
            nu=contamination_rate, 
            kernel='rbf', 
            gamma='scale'
        )
        self.models['One-Class SVM'].fit(X_scaled)
        
        self.is_trained = True
        print(f"Enhanced models trained successfully! (contamination: {contamination_rate})")
    
    def detect_statistical_anomalies(self, df, columns=None, threshold=3):
        """
        Enhanced statistical anomaly detection with QA integration
        """
        if columns is None:
            columns = ['TMAX_F', 'TMIN_F', 'PRCP_IN', 'TEMP_RANGE_F']
        
        anomalies = pd.DataFrame()
        
        for col in columns:
            if col in df.columns:
                # Use QA-aware threshold adjustment
                adjusted_threshold = threshold
                if self.qa_results['total_issues'] > 3:
                    adjusted_threshold = threshold + 0.5  # More lenient for stations with QA issues
                
                z_scores = np.abs(zscore(df[col].dropna()))
                anomaly_mask = z_scores > adjusted_threshold
                anomaly_indices = df[col].dropna().index[anomaly_mask]
                
                if len(anomaly_indices) > 0:
                    anomaly_data = df.loc[anomaly_indices, ['DATE', col]].copy()
                    anomaly_data['ANOMALY_TYPE'] = f'{col}_STATISTICAL'
                    anomaly_data['Z_SCORE'] = z_scores[anomaly_mask]
                    anomaly_data['QA_SCORE'] = df.loc[anomaly_indices, 'QA_SCORE'].values
                    anomalies = pd.concat([anomalies, anomaly_data], ignore_index=True)
        
        return anomalies
    
    def detect_ml_anomalies(self, df):
        """
        Enhanced ML anomaly detection with QA integration
        """
        if not self.is_trained:
            raise ValueError("Models must be trained before detecting anomalies")
        
        X = self.prepare_features(df)
        X_scaled = self.scaler.transform(X)
        
        ml_anomalies = {}
        
        for model_name, model in self.models.items():
            if model_name == 'Local Outlier Factor':
                predictions = model.fit_predict(X_scaled)
            else:
                predictions = model.predict(X_scaled)
            
            anomaly_indices = np.where(predictions == -1)[0]
            
            if len(anomaly_indices) > 0:
                anomaly_data = df.iloc[anomaly_indices][
                    ['DATE', 'TMAX_F', 'TMIN_F', 'PRCP_IN', 'TEMP_RANGE_F', 'QA_SCORE']
                ].copy()
                anomaly_data['MODEL'] = model_name
                ml_anomalies[model_name] = anomaly_data
        
        return ml_anomalies
    
    def detect_anomalies(self, df, use_statistical=True, use_ml=True, confidence_threshold=0.5):
        """
        Comprehensive anomaly detection with QA integration
        
        Args:
            df (pd.DataFrame): Raw weather data
            use_statistical (bool): Whether to use statistical methods
            use_ml (bool): Whether to use ML methods
            confidence_threshold (float): Confidence threshold for anomaly detection (0.0-1.0)
            
        Returns:
            dict: All detected anomalies
        """
        # Preprocess data with QA checks
        df_processed = self.preprocess_data(df)
        
        results = {}
        
        if use_statistical:
            results['statistical'] = self.detect_statistical_anomalies(df_processed)
        
        if use_ml and self.is_trained:
            results['ml'] = self.detect_ml_anomalies(df_processed)
        
        # Add QA results to output
        results['qa_results'] = self.qa_results
        
        # Add summary information
        results['summary'] = {
            'confidence_threshold': confidence_threshold,
            'data_quality_score': self.qa_results['qa_score'],
            'total_qa_issues': self.qa_results['total_issues'],
            'statistical_anomalies_count': len(results.get('statistical', [])),
            'ml_anomalies_count': sum(len(anomalies) for anomalies in results.get('ml', {}).values()),
            'total_anomalies': len(results.get('statistical', [])) + sum(len(anomalies) for anomalies in results.get('ml', {}).values())
        }
        
        return results
    
    def generate_qa_report(self):
        """
        Generate comprehensive QA report
        """
        if not self.qa_results:
            return "No QA results available. Run detect_anomalies() first."
        
        report = []
        report.append("=" * 60)
        report.append("GHCN-DAILY QUALITY ASSURANCE REPORT")
        report.append("=" * 60)
        
        report.append(f"\nOverall QA Score: {self.qa_results['qa_score']}/100")
        report.append(f"Total Issues Detected: {self.qa_results['total_issues']}")
        
        report.append("\nDetailed QA Results:")
        for category, issues in self.qa_results.items():
            if isinstance(issues, list) and len(issues) > 0:
                report.append(f"\n{category.upper().replace('_', ' ')}:")
                for issue in issues:
                    report.append(f"  - {issue}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def save_models(self, path):
        """
        Save enhanced models with QA results
        """
        if not self.is_trained:
            raise ValueError("No trained models to save")
        
        joblib.dump(self.models, f"{path}/models.pkl")
        joblib.dump(self.scaler, f"{path}/scaler.pkl")
        joblib.dump(self.feature_columns, f"{path}/feature_columns.pkl")
        joblib.dump(self.qa_results, f"{path}/qa_results.pkl")
        print(f"Enhanced models and QA results saved to {path}")
    
    def load_models(self, path):
        """
        Load enhanced models with QA results
        """
        try:
            self.models = joblib.load(f"{path}/models.pkl")
            self.scaler = joblib.load(f"{path}/scaler.pkl")
            self.feature_columns = joblib.load(f"{path}/feature_columns.pkl")
            self.qa_results = joblib.load(f"{path}/qa_results.pkl")
            self.is_trained = True
            print(f"Enhanced models and QA results loaded from {path}")
        except FileNotFoundError as e:
            print(f"Error loading models: {e}")
            self.is_trained = False

def main():
    """
    Example usage of the Enhanced WeatherAnomalyDetector
    """
    # Initialize enhanced detector
    detector = EnhancedWeatherAnomalyDetector()
    
    # Load data
    df = pd.read_csv('Datasets/GHCN_Data/Training_Data/ghcn_cleaned.csv')
    
    # Train models with QA integration
    df_processed = detector.preprocess_data(df)
    detector.train_models(df_processed)
    
    # Detect anomalies with QA integration
    anomalies = detector.detect_anomalies(df)
    
    # Print results
    print("\nEnhanced Anomaly Detection Results:")
    if 'statistical' in anomalies:
        print(f"Statistical anomalies: {len(anomalies['statistical'])}")
    
    if 'ml' in anomalies:
        for model_name, model_anomalies in anomalies['ml'].items():
            print(f"{model_name}: {len(model_anomalies)} anomalies")
    
    # Generate QA report
    print("\n" + detector.generate_qa_report())
    
    # Save enhanced models
    detector.save_models('enhanced_models')

if __name__ == "__main__":
    main()
