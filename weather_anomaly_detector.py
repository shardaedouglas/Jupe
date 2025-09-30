#!/usr/bin/env python3
"""
GHCN-D Weather Data Anomaly Detection System
Production-ready pipeline for real-time anomaly detection

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
import warnings
warnings.filterwarnings('ignore')

class WeatherAnomalyDetector:
    """
    A comprehensive anomaly detection system for GHCN-D weather data
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the anomaly detector
        
        Args:
            model_path (str): Path to saved model files
        """
        self.models = {}
        self.scaler = None
        self.feature_columns = None
        self.is_trained = False
        
        if model_path:
            self.load_models(model_path)
    
    def preprocess_data(self, df):
        """
        Preprocess weather data for anomaly detection
        
        Args:
            df (pd.DataFrame): Raw weather data
            
        Returns:
            pd.DataFrame: Processed data with engineered features
        """
        data = df.copy()
        
        # Convert DATE to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(data['DATE']):
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
        
        return data
    
    def prepare_features(self, df):
        """
        Prepare features for machine learning models
        
        Args:
            df (pd.DataFrame): Processed weather data
            
        Returns:
            np.ndarray: Feature matrix
        """
        if self.feature_columns is None:
            self.feature_columns = ['TMAX_F', 'TMIN_F', 'PRCP_IN', 'TEMP_RANGE_F', 
                                  'TMAX_7DAY_AVG_F', 'TMIN_7DAY_AVG_F', 'PRCP_7DAY_SUM_IN',
                                  'TMAX_SEASONAL_DEV_F', 'TMIN_SEASONAL_DEV_F', 'PRCP_SEASONAL_DEV_IN',
                                  'MONTH', 'DAY_OF_YEAR']
        
        X = df[self.feature_columns].copy()
        X = X.fillna(X.mean())
        
        return X
    
    def train_models(self, df):
        """
        Train multiple anomaly detection models
        
        Args:
            df (pd.DataFrame): Processed weather data
        """
        # Prepare features
        X = self.prepare_features(df)
        
        # Standardize features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models
        self.models['Isolation Forest'] = IsolationForest(
            contamination=0.1, random_state=42
        )
        self.models['Isolation Forest'].fit(X_scaled)
        
        self.models['Local Outlier Factor'] = LocalOutlierFactor(
            n_neighbors=20, contamination=0.1
        )
        
        self.models['One-Class SVM'] = OneClassSVM(
            nu=0.1, kernel='rbf', gamma='scale'
        )
        self.models['One-Class SVM'].fit(X_scaled)
        
        self.is_trained = True
        print("Models trained successfully!")
    
    def detect_statistical_anomalies(self, df, columns=None, threshold=3):
        """
        Detect anomalies using statistical methods (Z-score)
        
        Args:
            df (pd.DataFrame): Processed weather data
            columns (list): Columns to analyze
            threshold (float): Z-score threshold
            
        Returns:
            pd.DataFrame: Statistical anomalies
        """
        if columns is None:
            columns = ['TMAX_F', 'TMIN_F', 'PRCP_IN', 'TEMP_RANGE_F']
        
        anomalies = pd.DataFrame()
        
        for col in columns:
            if col in df.columns:
                z_scores = np.abs(zscore(df[col].dropna()))
                anomaly_mask = z_scores > threshold
                anomaly_indices = df[col].dropna().index[anomaly_mask]
                
                if len(anomaly_indices) > 0:
                    anomaly_data = df.loc[anomaly_indices, ['DATE', col]].copy()
                    anomaly_data['ANOMALY_TYPE'] = f'{col}_STATISTICAL'
                    anomaly_data['Z_SCORE'] = z_scores[anomaly_mask]
                    anomalies = pd.concat([anomalies, anomaly_data], ignore_index=True)
        
        return anomalies
    
    def detect_ml_anomalies(self, df):
        """
        Detect anomalies using machine learning models
        
        Args:
            df (pd.DataFrame): Processed weather data
            
        Returns:
            dict: Dictionary of anomalies by model
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
                    ['DATE', 'TMAX_F', 'TMIN_F', 'PRCP_IN', 'TEMP_RANGE_F']
                ].copy()
                anomaly_data['MODEL'] = model_name
                ml_anomalies[model_name] = anomaly_data
        
        return ml_anomalies
    
    def detect_anomalies(self, df, use_statistical=True, use_ml=True):
        """
        Comprehensive anomaly detection using both statistical and ML methods
        
        Args:
            df (pd.DataFrame): Raw weather data
            use_statistical (bool): Whether to use statistical methods
            use_ml (bool): Whether to use ML methods
            
        Returns:
            dict: All detected anomalies
        """
        # Preprocess data
        df_processed = self.preprocess_data(df)
        
        results = {}
        
        if use_statistical:
            results['statistical'] = self.detect_statistical_anomalies(df_processed)
        
        if use_ml and self.is_trained:
            results['ml'] = self.detect_ml_anomalies(df_processed)
        
        return results
    
    def save_models(self, path):
        """
        Save trained models to disk
        
        Args:
            path (str): Directory path to save models
        """
        if not self.is_trained:
            raise ValueError("No trained models to save")
        
        joblib.dump(self.models, f"{path}/models.pkl")
        joblib.dump(self.scaler, f"{path}/scaler.pkl")
        joblib.dump(self.feature_columns, f"{path}/feature_columns.pkl")
        print(f"Models saved to {path}")
    
    def load_models(self, path):
        """
        Load trained models from disk
        
        Args:
            path (str): Directory path containing saved models
        """
        try:
            self.models = joblib.load(f"{path}/models.pkl")
            self.scaler = joblib.load(f"{path}/scaler.pkl")
            self.feature_columns = joblib.load(f"{path}/feature_columns.pkl")
            self.is_trained = True
            print(f"Models loaded from {path}")
        except FileNotFoundError as e:
            print(f"Error loading models: {e}")
            self.is_trained = False

def main():
    """
    Example usage of the WeatherAnomalyDetector
    """
    # Initialize detector
    detector = WeatherAnomalyDetector()
    
    # Load data
    df = pd.read_csv('Datasets/GHCN_Data/Training_Data/ghcn_cleaned.csv')
    
    # Train models
    df_processed = detector.preprocess_data(df)
    detector.train_models(df_processed)
    
    # Detect anomalies
    anomalies = detector.detect_anomalies(df)
    
    # Print results
    print("\nAnomaly Detection Results:")
    if 'statistical' in anomalies:
        print(f"Statistical anomalies: {len(anomalies['statistical'])}")
    
    if 'ml' in anomalies:
        for model_name, model_anomalies in anomalies['ml'].items():
            print(f"{model_name}: {len(model_anomalies)} anomalies")
    
    # Save models for future use
    detector.save_models('models')

if __name__ == "__main__":
    main()
