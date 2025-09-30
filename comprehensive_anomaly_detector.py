"""
Comprehensive Weather Element Anomaly Detection for ADDIS
Author: Shardae Douglas
Date: 2025

This module provides anomaly detection for all GHCN weather elements
as defined in the GHCN readme.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ComprehensiveAnomalyDetector:
    """
    Comprehensive anomaly detector for all GHCN weather elements
    """
    
    def __init__(self):
        """Initialize the comprehensive anomaly detector"""
        
        # Define weather elements and their properties
        self.weather_elements = {
            # Core elements
            'TMAX': {'name': 'Maximum Temperature', 'unit': '°F', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'TMIN': {'name': 'Minimum Temperature', 'unit': '°F', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'PRCP': {'name': 'Precipitation', 'unit': 'inches', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            'SNOW': {'name': 'Snowfall', 'unit': 'mm', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            'SNWD': {'name': 'Snow Depth', 'unit': 'mm', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            
            # Additional elements
            'WESD': {'name': 'Water Equivalent of Snow on Ground', 'unit': 'mm', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            'WESF': {'name': 'Water Equivalent of Snowfall', 'unit': 'mm', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            'DAPR': {'name': 'Days of Precipitation', 'unit': 'days', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'MDPR': {'name': 'Multiday Precipitation Total', 'unit': 'mm', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            'EVAP': {'name': 'Evaporation', 'unit': 'mm', 'threshold_multiplier': 3.0, 'baseline_days': 30},
            'AWND': {'name': 'Average Wind Speed', 'unit': 'm/s', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'WSFG': {'name': 'Peak Wind Gust', 'unit': 'm/s', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'TAVG': {'name': 'Average Temperature', 'unit': '°F', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'ADPT': {'name': 'Average Dew Point Temperature', 'unit': '°F', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'ASLP': {'name': 'Average Sea Level Pressure', 'unit': 'hPa', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'RHAV': {'name': 'Average Relative Humidity', 'unit': '%', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'PSUN': {'name': 'Percent of Possible Sunshine', 'unit': '%', 'threshold_multiplier': 2.0, 'baseline_days': 30},
            'TSUN': {'name': 'Total Sunshine', 'unit': 'minutes', 'threshold_multiplier': 2.0, 'baseline_days': 30}
        }
        
        # Define element groups for different analysis approaches
        self.temperature_elements = ['TMAX', 'TMIN', 'TAVG', 'ADPT']
        self.precipitation_elements = ['PRCP', 'SNOW', 'SNWD', 'WESD', 'WESF', 'DAPR', 'MDPR', 'EVAP']
        self.wind_elements = ['AWND', 'WSFG', 'WSF1', 'WSF2', 'WSF5', 'WSFI', 'WSFM']
        self.pressure_elements = ['ASLP', 'ASTP']
        self.humidity_elements = ['RHAV', 'RHMN', 'RHMX']
        self.sunshine_elements = ['PSUN', 'TSUN']
    
    def get_available_elements(self, data: pd.DataFrame) -> List[str]:
        """
        Get list of available weather elements in the data
        
        Args:
            data: DataFrame with weather data
            
        Returns:
            List of available element names
        """
        available = []
        
        # Check for temperature elements (converted to Fahrenheit)
        if 'TMAX_F' in data.columns:
            available.append('TMAX_F')
        if 'TMIN_F' in data.columns:
            available.append('TMIN_F')
        if 'TAVG_F' in data.columns:
            available.append('TAVG_F')
        if 'ADPT_F' in data.columns:
            available.append('ADPT_F')
        
        # Check for precipitation elements (converted to inches)
        if 'PRCP_IN' in data.columns:
            available.append('PRCP_IN')
        elif 'PRCP' in data.columns:
            available.append('PRCP')
        
        # Check for other elements
        for element in ['SNOW', 'SNWD', 'WESD', 'WESF', 'DAPR', 'MDPR', 'EVAP', 'AWND', 'WSFG', 'ASLP', 'RHAV', 'PSUN', 'TSUN']:
            if element in data.columns:
                available.append(element)
        
        return available
    
    def calculate_element_baseline(self, data: pd.DataFrame, element: str, target_date: datetime) -> Optional[Dict]:
        """
        Calculate baseline statistics for a specific element and date
        
        Args:
            data: Historical weather data
            element: Weather element name
            target_date: Target date for baseline calculation
            
        Returns:
            Dictionary with baseline statistics or None if insufficient data
        """
        try:
            # Get baseline period (30 days before and after target date)
            baseline_start = target_date - timedelta(days=30)
            baseline_end = target_date + timedelta(days=30)
            
            # Filter data for baseline period
            baseline_data = data[
                (data['DATE'] >= baseline_start) & 
                (data['DATE'] <= baseline_end) &
                (data['DATE'] != target_date)  # Exclude target date
            ].copy()
            
            if baseline_data.empty:
                return None
            
            # Get element data
            element_data = baseline_data[element].dropna()
            
            if len(element_data) < 5:  # Need at least 5 valid readings
                return None
            
            # Calculate statistics
            mean_val = element_data.mean()
            std_val = element_data.std()
            
            if std_val == 0:  # Avoid division by zero
                return None
            
            return {
                'mean': float(mean_val),
                'std': float(std_val),
                'sample_size': len(element_data),
                'min': float(element_data.min()),
                'max': float(element_data.max()),
                'percentile_25': float(element_data.quantile(0.25)),
                'percentile_75': float(element_data.quantile(0.75))
            }
            
        except Exception as e:
            logger.error(f"Error calculating baseline for {element}: {e}")
            return None
    
    def detect_element_anomaly(self, value: float, baseline: Dict, element: str, confidence_threshold: float) -> Optional[Dict]:
        """
        Detect if a value is anomalous for a specific element
        
        Args:
            value: Observed value
            baseline: Baseline statistics
            element: Weather element name
            confidence_threshold: Confidence threshold for anomaly detection
            
        Returns:
            Dictionary with anomaly information or None if not anomalous
        """
        try:
            if pd.isna(value) or baseline is None:
                return None
            
            # Calculate Z-score
            z_score = (value - baseline['mean']) / baseline['std']
            
            # Check if value exceeds threshold
            threshold = confidence_threshold * baseline['std']
            
            if abs(z_score) > confidence_threshold:
                # Determine anomaly type
                if z_score > 0:
                    anomaly_type = "High"
                    severity = "extreme" if abs(z_score) > 3 else "moderate" if abs(z_score) > 2 else "mild"
                else:
                    anomaly_type = "Low"
                    severity = "extreme" if abs(z_score) > 3 else "moderate" if abs(z_score) > 2 else "mild"
                
                # Generate explanation
                explanation = self.generate_element_explanation(element, value, z_score, baseline, anomaly_type, severity)
                
                return {
                    'element': element,
                    'value': float(value),
                    'z_score': float(z_score),
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'explanation': explanation,
                    'baseline': baseline,
                    'threshold': float(threshold)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting anomaly for {element}: {e}")
            return None
    
    def generate_element_explanation(self, element: str, value: float, z_score: float, baseline: Dict, anomaly_type: str, severity: str) -> str:
        """
        Generate human-readable explanation for an anomaly
        
        Args:
            element: Weather element name
            value: Observed value
            z_score: Z-score
            baseline: Baseline statistics
            anomaly_type: Type of anomaly (High/Low)
            severity: Severity level
            
        Returns:
            Human-readable explanation
        """
        try:
            # Get element properties
            element_info = self.weather_elements.get(element, {'name': element, 'unit': 'units'})
            element_name = element_info['name']
            unit = element_info['unit']
            
            # Format values
            value_str = f"{value:.1f}{unit}"
            mean_str = f"{baseline['mean']:.1f}{unit}"
            std_str = f"{baseline['std']:.1f}{unit}"
            
            # Generate explanation based on element type
            if element in self.temperature_elements:
                if anomaly_type == "High":
                    explanation = f"<strong>This represents a {severity} high temperature</strong> for {element_name.lower()}. "
                    explanation += f"The observed value of {value_str} is significantly above the typical range of {mean_str} ± {std_str}. "
                else:
                    explanation = f"<strong>This represents a {severity} low temperature</strong> for {element_name.lower()}. "
                    explanation += f"The observed value of {value_str} is significantly below the typical range of {mean_str} ± {std_str}. "
                
                explanation += f"This temperature is in the {abs(z_score):.1f} standard deviation range, "
                explanation += f"which occurs approximately {self.get_frequency_description(abs(z_score))}."
                
            elif element in self.precipitation_elements:
                if anomaly_type == "High":
                    explanation = f"<strong>This represents {severity} high precipitation</strong> for {element_name.lower()}. "
                    explanation += f"The observed value of {value_str} is significantly above the typical range of {mean_str} ± {std_str}. "
                else:
                    explanation = f"<strong>This represents {severity} low precipitation</strong> for {element_name.lower()}. "
                    explanation += f"The observed value of {value_str} is significantly below the typical range of {mean_str} ± {std_str}. "
                
                explanation += f"This precipitation level is in the {abs(z_score):.1f} standard deviation range, "
                explanation += f"which occurs approximately {self.get_frequency_description(abs(z_score))}."
                
            elif element in self.wind_elements:
                if anomaly_type == "High":
                    explanation = f"<strong>This represents {severity} high wind</strong> for {element_name.lower()}. "
                    explanation += f"The observed value of {value_str} is significantly above the typical range of {mean_str} ± {std_str}. "
                else:
                    explanation = f"<strong>This represents {severity} low wind</strong> for {element_name.lower()}. "
                    explanation += f"The observed value of {value_str} is significantly below the typical range of {mean_str} ± {std_str}. "
                
                explanation += f"This wind level is in the {abs(z_score):.1f} standard deviation range, "
                explanation += f"which occurs approximately {self.get_frequency_description(abs(z_score))}."
                
            else:
                # Generic explanation for other elements
                explanation = f"<strong>This represents a {severity} {anomaly_type.lower()} value</strong> for {element_name.lower()}. "
                explanation += f"The observed value of {value_str} is significantly different from the typical range of {mean_str} ± {std_str}. "
                explanation += f"This value is in the {abs(z_score):.1f} standard deviation range, "
                explanation += f"which occurs approximately {self.get_frequency_description(abs(z_score))}."
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating explanation for {element}: {e}")
            return f"Anomalous {element_name.lower()} value detected."
    
    def get_frequency_description(self, z_score: float) -> str:
        """
        Get frequency description for a Z-score
        
        Args:
            z_score: Z-score value
            
        Returns:
            Frequency description
        """
        if z_score >= 3.0:
            return "less than 0.3% of the time"
        elif z_score >= 2.0:
            return "about 2.3% of the time"
        elif z_score >= 1.5:
            return "about 6.7% of the time"
        elif z_score >= 1.0:
            return "about 15.9% of the time"
        else:
            return "about 31.7% of the time"
    
    def detect_comprehensive_anomalies(self, data: pd.DataFrame, station_id: str, start_date: str, end_date: str, confidence_threshold: float = 1.0) -> Dict:
        """
        Detect anomalies for all available weather elements
        
        Args:
            data: Weather data DataFrame
            station_id: Station ID
            start_date: Start date for analysis
            end_date: End date for analysis
            confidence_threshold: Confidence threshold for anomaly detection
            
        Returns:
            Dictionary with comprehensive anomaly detection results
        """
        try:
            logger.info(f"Starting comprehensive anomaly detection for station {station_id}")
            
            # Parse date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # Filter data for analysis period
            analysis_data = data[
                (data['DATE'] >= start_dt) & 
                (data['DATE'] <= end_dt)
            ].copy()
            
            if analysis_data.empty:
                return {
                    'error': f'No data found for station {station_id} in the specified date range',
                    'station_id': station_id,
                    'date_range': f'{start_date} to {end_date}'
                }
            
            # Get available elements
            available_elements = self.get_available_elements(analysis_data)
            logger.info(f"Available elements for analysis: {available_elements}")
            
            if not available_elements:
                return {
                    'error': 'No analyzable weather elements found for this station',
                    'station_id': station_id
                }
            
            # Detect anomalies for each element
            all_anomalies = []
            element_summaries = {}
            
            for element in available_elements:
                logger.info(f"Analyzing element: {element}")
                element_anomalies = []
                
                for _, row in analysis_data.iterrows():
                    target_date = row['DATE']
                    value = row[element]
                    
                    # Calculate baseline for this element and date
                    baseline = self.calculate_element_baseline(data, element, target_date)
                    
                    if baseline is None:
                        continue
                    
                    # Detect anomaly
                    anomaly = self.detect_element_anomaly(value, baseline, element, confidence_threshold)
                    
                    if anomaly:
                        anomaly.update({
                            'DATE': target_date.strftime('%Y-%m-%d'),
                            'STATION': station_id
                        })
                        element_anomalies.append(anomaly)
                
                # Store element results
                if element_anomalies:
                    all_anomalies.extend(element_anomalies)
                
                # Create element summary
                element_data = analysis_data[element].dropna()
                if not element_data.empty:
                    element_summaries[element] = {
                        'total_records': len(element_data),
                        'anomalies_detected': len(element_anomalies),
                        'mean': float(element_data.mean()),
                        'std': float(element_data.std()),
                        'min': float(element_data.min()),
                        'max': float(element_data.max())
                    }
            
            # Sort anomalies by date
            all_anomalies.sort(key=lambda x: x['DATE'])
            
            # Create comprehensive summary
            summary = {
                'station_id': station_id,
                'analysis_period': f'{start_date} to {end_date}',
                'total_records': len(analysis_data),
                'total_anomalies': len(all_anomalies),
                'elements_analyzed': available_elements,
                'elements_with_anomalies': list(set([a['element'] for a in all_anomalies])),
                'confidence_threshold': confidence_threshold,
                'data_source': 'NCEI Dynamic Fetch'
            }
            
            return {
                'summary': summary,
                'element_summaries': element_summaries,
                'anomalies': {
                    'comprehensive': {
                        'anomalies': all_anomalies,
                        'total': len(all_anomalies)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive anomaly detection: {e}")
            return {
                'error': f'Error in comprehensive anomaly detection: {str(e)}',
                'station_id': station_id
            }


# Global instance
comprehensive_detector = ComprehensiveAnomalyDetector()
