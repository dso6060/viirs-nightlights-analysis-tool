"""
OpenStreetMap (OSM) Nominatim API service for geocoding.

Provides city search, autocomplete, and coordinate lookup functionality.
"""

import requests
import time
from typing import Dict, List, Optional
from urllib.parse import quote


class OSMService:
    """
    OpenStreetMap Nominatim geocoding service.
    
    Uses public Nominatim API with rate limiting compliance.
    """
    
    BASE_URL = "https://nominatim.openstreetmap.org"
    
    # Nominatim requires 1 request per second max
    MIN_REQUEST_INTERVAL = 1.0
    
    def __init__(self, user_agent: str = "VIIRSNightlightsApp/1.0"):
        """
        Initialize OSM service.
        
        Args:
            user_agent: User agent string for API requests
        """
        self.user_agent = user_agent
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce Nominatim rate limit (1 req/sec)."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        
        self.last_request_time = time.time()
    
    def geocode_city(
        self,
        city: str,
        country: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Geocode a city name to coordinates.
        
        Args:
            city: City name (e.g., "Berlin", "New York")
            country: Optional country name for disambiguation
        
        Returns:
            Dictionary with city info:
            {
                "city": str,
                "country": str,
                "display_name": str,
                "lat": float,
                "lon": float,
                "radius_km": float
            }
            Returns None if city not found.
        
        Raises:
            requests.HTTPError: If API request fails
        """
        self._rate_limit()
        
        # Build query
        if country:
            query = f"{city}, {country}"
        else:
            query = city
        
        # Request parameters
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        headers = {
            "User-Agent": self.user_agent
        }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/search",
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            
            if not results:
                return None
            
            result = results[0]
            
            # Extract location info
            address = result.get("address", {})
            
            # Determine country
            country_name = (
                address.get("country") or
                country or
                "Unknown"
            )
            
            # Determine city name
            city_name = (
                address.get("city") or
                address.get("town") or
                address.get("village") or
                address.get("municipality") or
                city
            )
            
            # Calculate appropriate radius based on place type
            place_type = result.get("type", "city")
            radius_km = self._estimate_radius(place_type)
            
            return {
                "city": city_name,
                "country": country_name,
                "display_name": result.get("display_name", f"{city_name}, {country_name}"),
                "lat": float(result["lat"]),
                "lon": float(result["lon"]),
                "radius_km": radius_km,
                "osm_id": result.get("osm_id"),
                "place_type": place_type
            }
        
        except requests.RequestException as e:
            print(f"OSM geocoding error: {e}")
            raise
    
    def search_cities(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for cities (autocomplete functionality).
        
        Args:
            query: Partial city name (e.g., "Berl")
            limit: Maximum number of results
        
        Returns:
            List of matching cities with basic info
        """
        self._rate_limit()
        
        params = {
            "q": query,
            "format": "json",
            "limit": limit,
            "addressdetails": 1,
            "featuretype": "city"
        }
        
        headers = {
            "User-Agent": self.user_agent
        }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/search",
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            
            # Format results
            cities = []
            for result in results:
                address = result.get("address", {})
                
                city_name = (
                    address.get("city") or
                    address.get("town") or
                    address.get("village") or
                    result.get("name")
                )
                
                country = address.get("country", "Unknown")
                
                cities.append({
                    "city": city_name,
                    "country": country,
                    "display_name": result.get("display_name"),
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"])
                })
            
            return cities
        
        except requests.RequestException as e:
            print(f"OSM search error: {e}")
            return []
    
    def reverse_geocode(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict]:
        """
        Reverse geocode coordinates to city name.
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            Dictionary with location info, or None if not found
        """
        self._rate_limit()
        
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1
        }
        
        headers = {
            "User-Agent": self.user_agent
        }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/reverse",
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                return None
            
            address = result.get("address", {})
            
            city_name = (
                address.get("city") or
                address.get("town") or
                address.get("village") or
                address.get("municipality") or
                "Unknown Location"
            )
            
            country = address.get("country", "Unknown")
            
            return {
                "city": city_name,
                "country": country,
                "display_name": result.get("display_name"),
                "lat": lat,
                "lon": lon
            }
        
        except requests.RequestException as e:
            print(f"OSM reverse geocode error: {e}")
            return None
    
    @staticmethod
    def _estimate_radius(place_type: str) -> float:
        """
        Estimate appropriate analysis radius based on place type.
        
        Args:
            place_type: OSM place type (city, town, village, etc.)
        
        Returns:
            Radius in kilometers
        """
        radius_map = {
            "city": 15.0,
            "town": 10.0,
            "village": 5.0,
            "municipality": 12.0,
            "administrative": 20.0,
            "hamlet": 3.0
        }
        
        return radius_map.get(place_type, 10.0)
    
    @staticmethod
    def parse_coordinate_string(coord_str: str) -> Optional[tuple]:
        """
        Parse coordinate string in various formats.
        
        Supports formats:
        - "52.52, 13.40"
        - "52.52,13.40"
        - "52.52 13.40"
        - "52.52N 13.40E"
        
        Args:
            coord_str: Coordinate string
        
        Returns:
            Tuple (lat, lon) or None if invalid
        """
        # Clean string
        coord_str = coord_str.strip().upper()
        
        # Remove direction letters
        coord_str = coord_str.replace('N', '').replace('S', '').replace('E', '').replace('W', '')
        
        # Try comma separator
        if ',' in coord_str:
            parts = coord_str.split(',')
        # Try space separator
        else:
            parts = coord_str.split()
        
        if len(parts) != 2:
            return None
        
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            
            # Validate ranges
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return None
            
            return (lat, lon)
        
        except ValueError:
            return None












