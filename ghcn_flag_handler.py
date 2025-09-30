"""
GHCN Flag Handler for ADDIS
Author: Shardae Douglas
Date: 2025

This module handles GHCN-Daily quality control flags (MFLAG, QFLAG, SFLAG)
according to the official GHCN-Daily format specification.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union

class GHCNFlagHandler:
    """
    Handles GHCN-Daily quality control flags according to the official specification.
    
    GHCN-Daily format uses three types of flags for each weather element:
    - MFLAG: Measurement flag (how the measurement was made)
    - QFLAG: Quality flag (quality assurance check results)
    - SFLAG: Source flag (data source identifier)
    """
    
    def __init__(self):
        """Initialize the flag handler with GHCN-Daily flag definitions."""
        self._init_measurement_flags()
        self._init_quality_flags()
        self._init_source_flags()
        self._init_source_priority()
    
    def _init_measurement_flags(self):
        """Initialize measurement flag definitions."""
        self.measurement_flags = {
            '': 'No measurement information applicable',
            'B': 'Precipitation total formed from two 12-hour totals',
            'D': 'Precipitation total formed from four six-hour totals',
            'H': 'Represents highest or lowest hourly temperature (TMAX or TMIN) or the average of hourly values (TAVG)',
            'K': 'Converted from knots',
            'L': 'Temperature appears to be lagged with respect to reported hour of observation',
            'O': 'Converted from oktas',
            'P': 'Identified as "missing presumed zero" in DSI 3200 and 3206',
            'T': 'Trace of precipitation, snowfall, or snow depth',
            'W': 'Converted from 16-point WBAN code (for wind direction)'
        }
    
    def _init_quality_flags(self):
        """Initialize quality flag definitions."""
        self.quality_flags = {
            '': 'Did not fail any quality assurance check',
            'D': 'Failed duplicate check',
            'G': 'Failed gap check',
            'I': 'Failed internal consistency check',
            'K': 'Failed streak/frequent-value check',
            'L': 'Failed check on length of multiday period',
            'M': 'Failed megaconsistency check',
            'N': 'Failed naught check',
            'O': 'Failed climatological outlier check',
            'R': 'Failed lagged range check',
            'S': 'Failed spatial consistency check',
            'T': 'Failed temporal consistency check',
            'W': 'Temperature too warm for snow',
            'X': 'Failed bounds check',
            'Z': 'Flagged as a result of an official Datzilla investigation'
        }
    
    def _init_source_flags(self):
        """Initialize source flag definitions."""
        self.source_flags = {
            '': 'No source (i.e., data value missing)',
            '0': 'U.S. Cooperative Summary of the Day (NCDC DSI-3200)',
            '6': 'CDMP Cooperative Summary of the Day (NCDC DSI-3206)',
            '7': 'U.S. Cooperative Summary of the Day -- Transmitted via WxCoder3 (NCDC DSI-3207)',
            'A': 'U.S. Automated Surface Observing System (ASOS) real-time data (since January 1, 2006)',
            'a': 'Australian data from the Australian Bureau of Meteorology',
            'B': 'U.S. ASOS data for October 2000-December 2005 (NCDC DSI-3211)',
            'b': 'Belarus update',
            'C': 'Environment Canada',
            'D': 'Short time delay US National Weather Service CF6 daily summaries provided by the High Plains Regional Climate Center',
            'd': 'Short time delay US National Weather Service Daily Summary Message (DSMs) provided by the High Plains Regional Climate Center',
            'E': 'European Climate Assessment and Dataset (Klein Tank et al., 2002)',
            'F': 'U.S. Fort data',
            'G': 'Official Global Climate Observing System (GCOS) or other government-supplied data',
            'H': 'High Plains Regional Climate Center real-time data',
            'I': 'International collection (non U.S. data received through personal contacts)',
            'K': 'U.S. Cooperative Summary of the Day data digitized from paper observer forms (from 2011 to present)',
            'M': 'Monthly METAR Extract (additional ASOS data)',
            'f': 'Data provided courtesy of the Fiji Met Service',
            'm': 'Data from the Mexican National Water Commission (Comision National del Agua -- CONAGUA)',
            'N': 'Community Collaborative Rain, Hail, and Snow (CoCoRaHS)',
            'Q': 'Data from several African countries that had been "quarantined", that is, withheld from public release until permission was granted from the respective meteorological services',
            'R': 'NCEI Reference Network Database (Climate Reference Network and Regional Climate Reference Network)',
            'r': 'All-Russian Research Institute of Hydrometeorological Information-World Data Center',
            'S': 'Global Summary of the Day (NCDC DSI-9618) - NOTE: "S" values are derived from hourly synoptic reports exchanged on the Global Telecommunications System (GTS). Daily values derived in this fashion may differ significantly from "true" daily data, particularly for precipitation (i.e., use with caution).',
            's': 'China Meteorological Administration/National Meteorological Information Center/Climatic Data Center',
            'T': 'SNOwpack TELemtry (SNOTEL) data obtained from the U.S. Department of Agriculture\'s Natural Resources Conservation Service',
            'U': 'Remote Automatic Weather Station (RAWS) data obtained from the Western Regional Climate Center',
            'u': 'Ukraine update',
            'W': 'WBAN/ASOS Summary of the Day from NCDC\'s Integrated Surface Data (ISD)',
            'X': 'U.S. First-Order Summary of the Day (NCDC DSI-3210)',
            'Z': 'Datzilla official additions or replacements',
            'z': 'Uzbekistan update'
        }
    
    def _init_source_priority(self):
        """Initialize source priority order (highest to lowest priority)."""
        self.source_priority = ['Z', 'R', 'D', '0', '6', 'C', 'X', 'W', 'K', '7', 'F', 'B', 'M', 'f', 'm', 'r', 'E', 'z', 'u', 'b', 's', 'a', 'G', 'Q', 'I', 'A', 'N', 'T', 'U', 'H', 'S']
    
    def parse_flags(self, attribute_string: str) -> Dict[str, str]:
        """
        Parse GHCN-Daily attribute string into individual flags.
        
        Args:
            attribute_string: String containing mflag,qflag,sflag format
            
        Returns:
            Dictionary with 'mflag', 'qflag', 'sflag' keys
        """
        if pd.isna(attribute_string) or attribute_string == '':
            return {'mflag': '', 'qflag': '', 'sflag': ''}
        
        # Handle different formats
        if isinstance(attribute_string, (int, float)):
            # If it's a number, treat as source flag only
            return {'mflag': '', 'qflag': '', 'sflag': str(int(attribute_string))}
        
        attribute_string = str(attribute_string).strip()
        
        # Split by comma if present
        if ',' in attribute_string:
            parts = attribute_string.split(',')
            mflag = parts[0].strip() if len(parts) > 0 else ''
            qflag = parts[1].strip() if len(parts) > 1 else ''
            sflag = parts[2].strip() if len(parts) > 2 else ''
        else:
            # Single character - assume it's a source flag
            mflag = ''
            qflag = ''
            sflag = attribute_string
        
        return {'mflag': mflag, 'qflag': qflag, 'sflag': sflag}
    
    def get_flag_description(self, flag_type: str, flag_value: str) -> str:
        """
        Get description for a specific flag.
        
        Args:
            flag_type: 'mflag', 'qflag', or 'sflag'
            flag_value: The flag character
            
        Returns:
            Description of the flag
        """
        if flag_type == 'mflag':
            return self.measurement_flags.get(flag_value, f'Unknown measurement flag: {flag_value}')
        elif flag_type == 'qflag':
            return self.quality_flags.get(flag_value, f'Unknown quality flag: {flag_value}')
        elif flag_type == 'sflag':
            return self.source_flags.get(flag_value, f'Unknown source flag: {flag_value}')
        else:
            return f'Unknown flag type: {flag_type}'
    
    def get_source_priority(self, sflag: str) -> int:
        """
        Get priority rank for a source flag (lower number = higher priority).
        
        Args:
            sflag: Source flag character
            
        Returns:
            Priority rank (0 = highest priority)
        """
        try:
            return self.source_priority.index(sflag)
        except ValueError:
            return len(self.source_priority)  # Lowest priority for unknown sources
    
    def is_quality_issue(self, qflag: str) -> bool:
        """
        Check if a quality flag indicates a quality issue.
        
        Args:
            qflag: Quality flag character
            
        Returns:
            True if there's a quality issue, False otherwise
        """
        return qflag != '' and qflag in self.quality_flags
    
    def is_high_quality_source(self, sflag: str) -> bool:
        """
        Check if a source flag represents a high-quality data source.
        
        Args:
            sflag: Source flag character
            
        Returns:
            True if it's a high-quality source, False otherwise
        """
        high_quality_sources = ['R', 'D', '0', '6', 'C', 'X', 'W', 'K', '7', 'F', 'B', 'M']
        return sflag in high_quality_sources
    
    def calculate_quality_score(self, mflag: str, qflag: str, sflag: str) -> float:
        """
        Calculate a quality score (0-100) based on flags.
        
        Args:
            mflag: Measurement flag
            qflag: Quality flag
            sflag: Source flag
            
        Returns:
            Quality score from 0 (lowest) to 100 (highest)
        """
        score = 100.0
        
        # Deduct points for quality issues
        if self.is_quality_issue(qflag):
            if qflag in ['D', 'G', 'I', 'K', 'L']:  # Minor issues
                score -= 10
            elif qflag in ['M', 'N', 'O', 'R', 'S', 'T']:  # Moderate issues
                score -= 25
            elif qflag in ['W', 'X', 'Z']:  # Major issues
                score -= 50
        
        # Adjust for source quality
        if not self.is_high_quality_source(sflag):
            score -= 15
        
        # Adjust for measurement flags
        if mflag in ['T']:  # Trace values
            score -= 5
        elif mflag in ['P']:  # Missing presumed zero
            score -= 20
        
        return max(0.0, score)
    
    def process_dataframe_flags(self, df: pd.DataFrame, element: str) -> pd.DataFrame:
        """
        Process flags for a specific weather element in a DataFrame.
        
        Args:
            df: DataFrame containing weather data
            element: Weather element ('PRCP', 'TMAX', 'TMIN', etc.)
            
        Returns:
            DataFrame with additional flag columns
        """
        attribute_col = f"{element}_ATTRIBUTES"
        
        if attribute_col not in df.columns:
            return df
        
        # Parse flags
        flag_data = df[attribute_col].apply(self.parse_flags)
        
        # Create new columns
        df[f"{element}_MFLAG"] = [flags['mflag'] for flags in flag_data]
        df[f"{element}_QFLAG"] = [flags['qflag'] for flags in flag_data]
        df[f"{element}_SFLAG"] = [flags['sflag'] for flags in flag_data]
        
        # Add quality score
        df[f"{element}_QUALITY_SCORE"] = [
            self.calculate_quality_score(flags['mflag'], flags['qflag'], flags['sflag'])
            for flags in flag_data
        ]
        
        # Add flag descriptions
        df[f"{element}_MFLAG_DESC"] = df[f"{element}_MFLAG"].apply(
            lambda x: self.get_flag_description('mflag', x)
        )
        df[f"{element}_QFLAG_DESC"] = df[f"{element}_QFLAG"].apply(
            lambda x: self.get_flag_description('qflag', x)
        )
        df[f"{element}_SFLAG_DESC"] = df[f"{element}_SFLAG"].apply(
            lambda x: self.get_flag_description('sflag', x)
        )
        
        return df
    
    def get_quality_summary(self, df: pd.DataFrame, element: str) -> Dict:
        """
        Get quality summary for a weather element.
        
        Args:
            df: DataFrame containing weather data
            element: Weather element ('PRCP', 'TMAX', 'TMIN', etc.)
            
        Returns:
            Dictionary with quality statistics
        """
        qflag_col = f"{element}_QFLAG"
        quality_score_col = f"{element}_QUALITY_SCORE"
        
        if qflag_col not in df.columns:
            return {}
        
        total_records = len(df)
        quality_issues = df[qflag_col].apply(self.is_quality_issue).sum()
        avg_quality_score = df[quality_score_col].mean() if quality_score_col in df.columns else 0
        
        # Count quality issues by type
        quality_issue_counts = {}
        for qflag in df[qflag_col].unique():
            if self.is_quality_issue(qflag):
                count = (df[qflag_col] == qflag).sum()
                quality_issue_counts[qflag] = {
                    'count': count,
                    'description': self.get_flag_description('qflag', qflag)
                }
        
        return {
            'total_records': total_records,
            'quality_issues': quality_issues,
            'quality_issue_rate': quality_issues / total_records if total_records > 0 else 0,
            'average_quality_score': avg_quality_score,
            'quality_issue_breakdown': quality_issue_counts
        }


def enhance_data_with_ghcn_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhance a DataFrame with GHCN flag processing.
    
    Args:
        df: DataFrame containing weather data with _ATTRIBUTES columns
        
    Returns:
        Enhanced DataFrame with parsed flags and quality scores
    """
    handler = GHCNFlagHandler()
    
    # Process flags for each weather element
    elements = ['PRCP', 'TMAX', 'TMIN']
    for element in elements:
        if f"{element}_ATTRIBUTES" in df.columns:
            df = handler.process_dataframe_flags(df, element)
    
    return df


def get_ghcn_flag_summary(df: pd.DataFrame) -> Dict:
    """
    Get comprehensive GHCN flag summary for a dataset.
    
    Args:
        df: DataFrame containing weather data
        
    Returns:
        Dictionary with comprehensive flag analysis
    """
    handler = GHCNFlagHandler()
    
    summary = {
        'elements_processed': [],
        'overall_quality': {},
        'element_quality': {}
    }
    
    elements = ['PRCP', 'TMAX', 'TMIN']
    for element in elements:
        if f"{element}_ATTRIBUTES" in df.columns:
            summary['elements_processed'].append(element)
            summary['element_quality'][element] = handler.get_quality_summary(df, element)
    
    # Calculate overall quality metrics
    if summary['elements_processed']:
        all_quality_scores = []
        for element in summary['elements_processed']:
            quality_score_col = f"{element}_QUALITY_SCORE"
            if quality_score_col in df.columns:
                all_quality_scores.extend(df[quality_score_col].dropna().tolist())
        
        if all_quality_scores:
            summary['overall_quality'] = {
                'average_quality_score': np.mean(all_quality_scores),
                'min_quality_score': np.min(all_quality_scores),
                'max_quality_score': np.max(all_quality_scores),
                'total_records': len(all_quality_scores)
            }
    
    return summary


if __name__ == "__main__":
    # Test the flag handler
    handler = GHCNFlagHandler()
    
    # Test flag parsing
    test_flags = ["", "6", "B,D,0", "T,,S"]
    for flag in test_flags:
        parsed = handler.parse_flags(flag)
        print(f"Input: '{flag}' -> Parsed: {parsed}")
    
    # Test quality score calculation
    test_cases = [
        ("", "", "0"),  # Perfect quality
        ("", "O", "0"),  # Quality issue
        ("T", "", "S"),  # Trace measurement
        ("", "X", "S")   # Major quality issue
    ]
    
    for mflag, qflag, sflag in test_cases:
        score = handler.calculate_quality_score(mflag, qflag, sflag)
        print(f"Flags: M={mflag}, Q={qflag}, S={sflag} -> Quality Score: {score}")
