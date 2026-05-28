"""
Bias correction for VIIRS nighttime lights data.
Implements Elvidge et al. (2021) cloud bias correction methodology.

Reference:
Elvidge, C. D., Zhizhin, M., Ghosh, T., Hsu, F. C., & Taneja, J. (2021).
"But clouds got in my way: Bias and bias correction of VIIRS nighttime lights data."
Remote Sensing of Environment, 258, 112165.
https://doi.org/10.1016/j.rse.2021.112165
"""

import numpy as np
from typing import Union


class BiasCorrection:
    """
    VIIRS nighttime lights bias correction.
    
    The Elvidge et al. (2021) methodology corrects for cloud cover bias
    in monthly composite radiance data.
    """
    
    # Empirically determined correction factor (Elvidge et al. 2021)
    ALPHA = 0.2
    
    # Fallback correction when cloud coverage data unavailable
    FALLBACK_FACTOR = 1.15
    
    @staticmethod
    def apply_correction(
        radiance: Union[float, np.ndarray],
        cloud_free_coverage: Union[float, np.ndarray, None] = None
    ) -> Union[float, np.ndarray]:
        """
        Apply bias correction to radiance values.
        
        Formula: corrected = radiance * (1 + α * (1 - cf_cvg/100))
        
        Args:
            radiance: Raw radiance value(s) in nW/cm²/sr
            cloud_free_coverage: Cloud-free coverage percentage (0-100)
                                If None, uses fallback correction
        
        Returns:
            Bias-corrected radiance value(s)
        """
        # Validate radiance
        if isinstance(radiance, np.ndarray):
            radiance = BiasCorrection._validate_radiance_array(radiance)
        else:
            radiance = BiasCorrection._validate_radiance_scalar(radiance)
        
        # Apply correction
        if cloud_free_coverage is None:
            # No cloud data available - use simple fallback
            return radiance * BiasCorrection.FALLBACK_FACTOR
        
        # Validate cloud coverage
        if isinstance(cloud_free_coverage, np.ndarray):
            cloud_free_coverage = np.clip(cloud_free_coverage, 0, 100)
        else:
            cloud_free_coverage = max(0, min(100, cloud_free_coverage))
        
        # Handle zero or invalid coverage
        if isinstance(cloud_free_coverage, (int, float)):
            if cloud_free_coverage <= 0:
                return radiance * BiasCorrection.FALLBACK_FACTOR
        
        # Apply Elvidge et al. (2021) correction
        correction_factor = 1 + BiasCorrection.ALPHA * (1 - cloud_free_coverage / 100)
        corrected = radiance * correction_factor
        
        return corrected
    
    @staticmethod
    def _validate_radiance_scalar(radiance: float) -> float:
        """Validate and clean single radiance value."""
        if radiance is None or np.isnan(radiance) or radiance < 0:
            return 0.0
        return max(0.0, radiance)
    
    @staticmethod
    def _validate_radiance_array(radiance: np.ndarray) -> np.ndarray:
        """Validate and clean radiance array."""
        # Replace NaN and negative values with 0
        radiance = np.where(np.isnan(radiance), 0, radiance)
        radiance = np.where(radiance < 0, 0, radiance)
        return radiance
    
    @staticmethod
    def calculate_seasonal_adjustment(
        radiance: float,
        month: int,
        latitude: float
    ) -> float:
        """
        Apply seasonal adjustment for high-latitude regions.
        
        Higher latitudes have significant seasonal variations in
        nighttime length, affecting radiance measurements.
        
        Args:
            radiance: Raw radiance value
            month: Month number (1-12)
            latitude: Latitude in degrees
        
        Returns:
            Seasonally adjusted radiance
        """
        # No adjustment for tropical/subtropical regions
        if abs(latitude) < 40:
            return radiance
        
        # Seasonal factor varies with month
        # Northern hemisphere: darker in summer, brighter in winter
        # Southern hemisphere: opposite
        seasonal_factors = {
            1: 1.0, 2: 1.0, 3: 0.95, 4: 0.9, 5: 0.85, 6: 0.8,
            7: 0.8, 8: 0.85, 9: 0.9, 10: 0.95, 11: 1.0, 12: 1.0
        }
        
        factor = seasonal_factors.get(month, 1.0)
        
        # Invert for southern hemisphere
        if latitude < 0:
            # Shift by 6 months
            month_shifted = ((month + 6 - 1) % 12) + 1
            factor = seasonal_factors.get(month_shifted, 1.0)
        
        return radiance / factor
    
    @staticmethod
    def remove_outliers(
        radiance_array: np.ndarray,
        method: str = "iqr",
        threshold: float = 1.5
    ) -> np.ndarray:
        """
        Remove outliers from radiance data.
        
        Args:
            radiance_array: Array of radiance values
            method: "iqr" (interquartile range) or "zscore"
            threshold: Outlier threshold (1.5 for IQR, 3 for z-score)
        
        Returns:
            Array with outliers replaced by NaN
        """
        if len(radiance_array) == 0:
            return radiance_array
        
        if method == "iqr":
            q1 = np.nanpercentile(radiance_array, 25)
            q3 = np.nanpercentile(radiance_array, 75)
            iqr = q3 - q1
            
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            outliers = (radiance_array < lower_bound) | (radiance_array > upper_bound)
            
        elif method == "zscore":
            mean = np.nanmean(radiance_array)
            std = np.nanstd(radiance_array)
            
            if std == 0:
                return radiance_array
            
            z_scores = np.abs((radiance_array - mean) / std)
            outliers = z_scores > threshold
        
        else:
            raise ValueError(f"Unknown outlier method: {method}")
        
        # Replace outliers with NaN
        cleaned = radiance_array.copy()
        cleaned[outliers] = np.nan
        
        return cleaned












