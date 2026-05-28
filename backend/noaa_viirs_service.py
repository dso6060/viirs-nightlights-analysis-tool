"""
NOAA Earth Observation Group (EOG) VIIRS data service.

Direct HTTP access to VIIRS DNB monthly composites with on-the-fly processing.
"""

import os
import re
import requests
import rasterio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from bs4 import BeautifulSoup
from rasterio.windows import from_bounds
from rasterio.crs import CRS
from pyproj import Transformer

from bias_correction import BiasCorrection


class NOAAVIIRSService:
    """
    NOAA EOG VIIRS nighttime lights data service.
    
    Downloads and processes monthly composite GeoTIFF files on-demand.
    """
    
    BASE_URL = "https://eogdata.mines.edu/nighttime_light/monthly/v10"
    
    # Global tile coverage (6 tiles cover entire Earth)
    TILES = {
        '75N180W': {'lat_range': (0, 75), 'lon_range': (-180, -60)},
        '75N060W': {'lat_range': (0, 75), 'lon_range': (-60, 60)},
        '75N060E': {'lat_range': (0, 75), 'lon_range': (60, 180)},
        '00N180W': {'lat_range': (-65, 0), 'lon_range': (-180, -60)},
        '00N060W': {'lat_range': (-65, 0), 'lon_range': (-60, 60)},
        '00N060E': {'lat_range': (-65, 0), 'lon_range': (60, 180)}
    }
    
    def __init__(self, cache_dir: str = "/tmp/viirs_cache"):
        """
        Initialize NOAA VIIRS service.
        
        Args:
            cache_dir: Directory for caching downloaded tiles
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate cache for tiles and results
        self.tile_cache = self.cache_dir / "tiles"
        self.results_cache = self.cache_dir / "results"
        self.tile_cache.mkdir(exist_ok=True)
        self.results_cache.mkdir(exist_ok=True)
    
    def get_tile_for_location(self, lat: float, lon: float) -> str:
        """
        Determine which NOAA tile contains the given coordinates.
        
        Args:
            lat: Latitude (-65 to 75)
            lon: Longitude (-180 to 180)
        
        Returns:
            Tile name (e.g., "75N060W")
        
        Raises:
            ValueError: If coordinates outside VIIRS coverage
        """
        # Validate latitude range
        if lat < -65 or lat > 75:
            raise ValueError(
                f"Latitude {lat}° outside VIIRS coverage (-65° to 75°N)"
            )
        
        # Find matching tile
        for tile_name, bounds in self.TILES.items():
            lat_min, lat_max = bounds['lat_range']
            lon_min, lon_max = bounds['lon_range']
            
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return tile_name
        
        raise ValueError(f"No tile found for coordinates: ({lat}, {lon})")
    
    def fetch_viirs_for_city(
        self,
        city_name: str,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        start_date: str = "2019-01",
        end_date: str = "2024-12"
    ) -> List[Dict]:
        """
        Fetch VIIRS data for a city from NOAA EOG.
        
        Args:
            city_name: Name of city
            lat: City latitude
            lon: City longitude
            radius_km: Analysis radius in kilometers
            start_date: Start date (YYYY-MM format)
            end_date: End date (YYYY-MM format)
        
        Returns:
            List of data points:
            [
                {
                    "date": "YYYY-MM",
                    "city": str,
                    "country": str,
                    "latitude": float,
                    "longitude": float,
                    "radiance": float,
                    "radiance_corrected": float,
                    "cloud_free_coverage": float (optional)
                },
                ...
            ]
        """
        # Determine tile
        tile_name = self.get_tile_for_location(lat, lon)
        
        # Generate date range
        dates = self._generate_date_range(start_date, end_date)
        
        results = []
        
        for date_str in dates:
            try:
                print(f"Processing {city_name} for {date_str}...")
                
                # Process month
                data_point = self._process_month(
                    tile_name=tile_name,
                    date_str=date_str,
                    lat=lat,
                    lon=lon,
                    radius_km=radius_km,
                    city_name=city_name
                )
                
                if data_point:
                    results.append(data_point)
            
            except Exception as e:
                print(f"Warning: Failed to process {date_str}: {e}")
                continue
        
        return results
    
    def _process_month(
        self,
        tile_name: str,
        date_str: str,
        lat: float,
        lon: float,
        radius_km: float,
        city_name: str
    ) -> Optional[Dict]:
        """
        Download and process data for one month.
        
        Args:
            tile_name: NOAA tile name
            date_str: Date in YYYY-MM format
            lat: Latitude
            lon: Longitude
            radius_km: Radius in km
            city_name: City name
        
        Returns:
            Data point dictionary or None if failed
        """
        year, month = date_str.split("-")
        yearmonth = f"{year}{month}"

        # 1) Find file URLs for avg radiance and cloud-free coverage
        base_path = f"{self.BASE_URL}/{year}/"
        avg_url = self._find_file_url(
            base_path=base_path,
            yearmonth=yearmonth,
            tile_name=tile_name,
            band="avg_rade9",
        )
        cf_url = self._find_file_url(
            base_path=base_path,
            yearmonth=yearmonth,
            tile_name=tile_name,
            band="cf_cvg",
        )

        if not avg_url:
            raise RuntimeError(
                f"Real-data mode: could not locate avg_rade9 GeoTIFF for {date_str}/{tile_name}"
            )

        # 2) Extract region arrays
        avg_arr = self._download_and_extract_region(avg_url, lat, lon, radius_km)
        if avg_arr is None:
            raise RuntimeError(
                f"Real-data mode: failed to extract avg_rade9 region for {date_str}/{tile_name}"
            )

        cf_arr = None
        if cf_url:
            cf_arr = self._download_and_extract_region(cf_url, lat, lon, radius_km)

        # 3) Aggregate
        if not np.any(~np.isnan(avg_arr)):
            raise RuntimeError(
                f"Real-data mode: extracted region contains no valid radiance pixels for {city_name} {date_str}"
            )

        avg_radiance = float(np.nanmean(avg_arr))

        # Prefer cf_cvg band if available; otherwise approximate with valid-pixel ratio.
        if cf_arr is not None and np.any(~np.isnan(cf_arr)):
            cf_cvg = float(np.nanmean(cf_arr))
        else:
            valid_pixels = int(np.sum(~np.isnan(avg_arr)))
            total_pixels = int(avg_arr.size)
            cf_cvg = (valid_pixels / max(1, total_pixels)) * 100.0

        corrected_radiance = BiasCorrection.apply_correction(avg_radiance, cf_cvg)

        return {
            "date": date_str,
            "city": city_name,
            "latitude": lat,
            "longitude": lon,
            "radiance": avg_radiance,
            "radiance_corrected": float(corrected_radiance),
            "cloud_free_coverage": cf_cvg,
        }
    
    def _find_file_url(
        self,
        base_path: str,
        yearmonth: str,
        tile_name: str,
        band: str
    ) -> Optional[str]:
        """
        Find the exact filename by scraping directory listing.
        
        NOAA uses varying date suffixes (e.g., c202412050000),
        so we need to find the actual filename.
        
        Args:
            base_path: Base directory URL
            yearmonth: YYYYMM string
            tile_name: Tile identifier
            band: Data band (avg_rade9 or cf_cvg)
        
        Returns:
            Full file URL or None if not found
        """
        try:
            # Try common day-of-month values
            for day in [15, 1, 28]:
                # Pattern: SVDNB_npp_YYYYMMDD_TILE_vcmslcfg_v10_c*.BAND.tif
                pattern = f"SVDNB_npp_{yearmonth}{day:02d}_{tile_name}_vcmslcfg_v10"
                
                # Try to list directory
                response = requests.get(base_path, timeout=10)
                
                if response.status_code != 200:
                    continue
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find matching files
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if pattern in href and f".{band}.tif" in href:
                        return f"{base_path}/{href}"
            
            return None
        
        except Exception as e:
            print(f"Error finding file: {e}")
            return None
    
    def _download_and_extract_region(
        self,
        url: str,
        lat: float,
        lon: float,
        radius_km: float
    ) -> Optional[np.ndarray]:
        """
        Download GeoTIFF and extract region around coordinates.
        
        Args:
            url: File URL
            lat: Center latitude
            lon: Center longitude
            radius_km: Extraction radius in km
        
        Returns:
            Numpy array of extracted data, or None if failed
        """
        # Check cache
        filename = url.split('/')[-1]
        cache_file = self.tile_cache / filename
        
        # Download if not cached
        if not cache_file.exists():
            try:
                print(f"Downloading: {filename}")
                response = requests.get(url, stream=True, timeout=120)
                response.raise_for_status()
                
                # Save to cache
                with open(cache_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"Cached: {filename}")
            
            except Exception as e:
                print(f"Download failed: {e}")
                return None
        
        # Read GeoTIFF and extract region
        try:
            with rasterio.open(cache_file) as src:
                return self._extract_region(src, lat, lon, radius_km)
        
        except Exception as e:
            print(f"GeoTIFF read error: {e}")
            # Delete corrupted file
            if cache_file.exists():
                cache_file.unlink()
            return None
    
    def _extract_region(
        self,
        src: rasterio.DatasetReader,
        lat: float,
        lon: float,
        radius_km: float
    ) -> Optional[np.ndarray]:
        """
        Extract data within radius of target coordinates.
        
        Handles CRS transformation from WGS84 to GeoTIFF projection.
        
        Args:
            src: Rasterio dataset reader
            lat: Target latitude
            lon: Target longitude
            radius_km: Extraction radius in km
        
        Returns:
            Extracted data array
        """
        # Check if CRS transformation needed
        if src.crs != CRS.from_epsg(4326):
            # Transform coordinates
            transformer = Transformer.from_crs(
                CRS.from_epsg(4326),  # WGS84
                src.crs,
                always_xy=True
            )
            lon_proj, lat_proj = transformer.transform(lon, lat)
        else:
            lon_proj, lat_proj = lon, lat
        
        # Convert radius to degrees (approximate)
        radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km
        
        # Define bounding box
        try:
            window = from_bounds(
                lon_proj - radius_deg,
                lat_proj - radius_deg,
                lon_proj + radius_deg,
                lat_proj + radius_deg,
                transform=src.transform
            )
            
            # Read data
            data = src.read(1, window=window)
            
            # Mask invalid values (negative radiance, fill values)
            data = np.where(data < 0, np.nan, data)
            data = np.where(data > 1e10, np.nan, data)
            
            return data
        
        except Exception as e:
            print(f"Region extraction error: {e}")
            return None
    
    def _generate_date_range(self, start: str, end: str) -> List[str]:
        """
        Generate list of YYYY-MM dates between start and end.
        
        Args:
            start: Start date (YYYY-MM)
            end: End date (YYYY-MM)
        
        Returns:
            List of date strings
        """
        start_date = datetime.strptime(start, "%Y-%m")
        end_date = datetime.strptime(end, "%Y-%m")
        
        dates = []
        current = start_date
        
        while current <= end_date:
            dates.append(current.strftime("%Y-%m"))
            
            # Increment by one month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return dates
    
    def get_latest_available_month(self) -> Dict[str, int]:
        """
        Determine the latest available VIIRS data month.
        
        NOAA typically has 1-2 month processing lag.
        
        Returns:
            {"year": int, "month": int}
        """
        # Estimate: current month - 2 months
        current = datetime.now()
        latest = current - timedelta(days=60)
        
        return {
            "year": latest.year,
            "month": latest.month
        }
    
    def cleanup_old_cache(self, days: int = 30):
        """
        Remove cached files older than specified days.
        
        Args:
            days: Age threshold in days
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff.timestamp()
        
        for cache_file in self.tile_cache.iterdir():
            if cache_file.is_file():
                if cache_file.stat().st_mtime < cutoff_timestamp:
                    print(f"Removing old cache: {cache_file.name}")
                    cache_file.unlink()

