"""
FastAPI application for VIIRS nightlights data service.

Provides RESTful API endpoints for fetching and processing VIIRS data.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uvicorn
from datetime import datetime
import os

from noaa_viirs_service import NOAAVIIRSService
from osm_service import OSMService
from bias_correction import BiasCorrection


# Initialize FastAPI app
app = FastAPI(
    title="VIIRS Nightlights Analysis Tool",
    description="Direct NOAA EOG VIIRS data access with on-the-fly processing",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    # IMPORTANT: do not use "*" in production. Set CORS_ORIGINS to your domain(s).
    allow_origins=[o.strip() for o in (os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost").split(",")) if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
viirs_service = NOAAVIIRSService()
osm_service = OSMService()


# Request/Response Models
class CityRequest(BaseModel):
    city: str = Field(..., description="City name")
    country: Optional[str] = Field(None, description="Country name (optional)")
    start_month: int = Field(1, ge=1, le=12, description="Start month (1-12)")
    start_year: int = Field(2019, ge=2012, le=2025, description="Start year")
    end_month: int = Field(12, ge=1, le=12, description="End month (1-12)")
    end_year: int = Field(2024, ge=2012, le=2025, description="End year")


class MultiCityRequest(BaseModel):
    cities: List[str] = Field(..., max_length=5, description="List of city names (max 5)")
    start_month: int = Field(1, ge=1, le=12)
    start_year: int = Field(2019, ge=2012, le=2025)
    end_month: int = Field(12, ge=1, le=12)
    end_year: int = Field(2024, ge=2012, le=2025)


class CoordinatesRequest(BaseModel):
    latitude: float = Field(..., ge=-65, le=75, description="Latitude (-65 to 75)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    radius_km: float = Field(10.0, gt=0, le=50, description="Radius in km")
    start_month: int = Field(1, ge=1, le=12)
    start_year: int = Field(2019, ge=2012, le=2025)
    end_month: int = Field(12, ge=1, le=12)
    end_year: int = Field(2024, ge=2012, le=2025)


# API Endpoints
@app.get("/")
def root():
    """API information and health check."""
    return {
        "name": "VIIRS Nightlights Analysis Tool",
        "version": "1.0.0",
        "description": "Direct NOAA EOG access with bias correction",
        "features": [
            "OSM-based geocoding",
            "Direct NOAA EOG queries",
            "On-the-fly bias correction (Elvidge et al. 2021)",
            "Multi-city comparison",
            "Monthly granularity (2012-present)"
        ],
        "data_source": "NOAA Earth Observation Group",
        "endpoints": {
            "GET /": "API info",
            "GET /viirs/latest-available": "Get latest available data month",
            "POST /viirs/city": "Fetch VIIRS data for a city",
            "POST /viirs/cities": "Fetch VIIRS data for multiple cities",
            "POST /viirs/coordinates": "Fetch VIIRS data for coordinates",
            "GET /search": "City autocomplete search"
        }
    }


@app.get("/viirs/latest-available")
def get_latest_available():
    """
    Get the latest available VIIRS data month.
    
    Returns:
        {"year": int, "month": int, "date_string": "YYYY-MM"}
    """
    try:
        latest = viirs_service.get_latest_available_month()
        return {
            "year": latest["year"],
            "month": latest["month"],
            "date_string": f"{latest['year']}-{latest['month']:02d}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/viirs/city")
def fetch_city_data(request: CityRequest):
    """
    Fetch VIIRS data for a single city.
    
    Args:
        request: City request with date range
    
    Returns:
        {
            "status": "success",
            "city_info": {...},
            "data": [...],
            "metadata": {...}
        }
    """
    try:
        # Validate date range
        start_date = f"{request.start_year}-{request.start_month:02d}"
        end_date = f"{request.end_year}-{request.end_month:02d}"
        
        if not _validate_date_range(start_date, end_date):
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Geocode city
        print(f"Geocoding: {request.city}, {request.country}")
        city_info = osm_service.geocode_city(request.city, request.country)
        
        if not city_info:
            raise HTTPException(
                status_code=404,
                detail=f"City '{request.city}' not found. Try different spelling or add country."
            )
        
        # Fetch VIIRS data
        print(f"Fetching VIIRS data from NOAA...")
        viirs_data = viirs_service.fetch_viirs_for_city(
            city_name=city_info['city'],
            lat=city_info['lat'],
            lon=city_info['lon'],
            radius_km=city_info['radius_km'],
            start_date=start_date,
            end_date=end_date
        )
        
        # Add country to each data point
        for point in viirs_data:
            point['country'] = city_info['country']
        
        return {
            "status": "success",
            "city_info": city_info,
            "data": viirs_data,
            "metadata": {
                "baseline_year": request.start_year,
                "data_points": len(viirs_data),
                "data_source": "NOAA Earth Observation Group",
                "bias_correction": "Elvidge et al. (2021)",
                "processing": "On-the-fly"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching data: {str(e)}"
        )


@app.post("/viirs/cities")
def fetch_multi_city_data(request: MultiCityRequest):
    """
    Fetch VIIRS data for multiple cities.
    
    Processes cities in parallel where possible.
    
    Args:
        request: Multi-city request
    
    Returns:
        {
            "status": "success",
            "cities": [...],
            "data": [...],
            "errors": [...]
        }
    """
    if len(request.cities) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 cities per request"
        )
    
    start_date = f"{request.start_year}-{request.start_month:02d}"
    end_date = f"{request.end_year}-{request.end_month:02d}"
    
    if not _validate_date_range(start_date, end_date):
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )
    
    results = []
    errors = []
    all_data = []
    
    for city_name in request.cities:
        try:
            # Geocode
            city_info = osm_service.geocode_city(city_name)
            
            if not city_info:
                errors.append({
                    "city": city_name,
                    "error": "City not found"
                })
                continue
            
            # Fetch data
            viirs_data = viirs_service.fetch_viirs_for_city(
                city_name=city_info['city'],
                lat=city_info['lat'],
                lon=city_info['lon'],
                radius_km=city_info['radius_km'],
                start_date=start_date,
                end_date=end_date
            )
            
            # Add country
            for point in viirs_data:
                point['country'] = city_info['country']
            
            results.append(city_info)
            all_data.extend(viirs_data)
        
        except Exception as e:
            errors.append({
                "city": city_name,
                "error": str(e)
            })
    
    return {
        "status": "success" if results else "error",
        "cities": results,
        "data": all_data,
        "errors": errors if errors else None,
        "metadata": {
            "cities_processed": len(results),
            "cities_failed": len(errors),
            "total_data_points": len(all_data)
        }
    }


@app.post("/viirs/coordinates")
def fetch_coordinates_data(request: CoordinatesRequest):
    """
    Fetch VIIRS data for specific coordinates.
    
    Args:
        request: Coordinates request
    
    Returns:
        Similar to /viirs/city endpoint
    """
    try:
        start_date = f"{request.start_year}-{request.start_month:02d}"
        end_date = f"{request.end_year}-{request.end_month:02d}"
        
        if not _validate_date_range(start_date, end_date):
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Reverse geocode to get location name
        location_info = osm_service.reverse_geocode(
            request.latitude,
            request.longitude
        )
        
        city_name = location_info['city'] if location_info else "Custom Location"
        country_name = location_info['country'] if location_info else "Unknown"
        
        # Fetch VIIRS data
        viirs_data = viirs_service.fetch_viirs_for_city(
            city_name=city_name,
            lat=request.latitude,
            lon=request.longitude,
            radius_km=request.radius_km,
            start_date=start_date,
            end_date=end_date
        )
        
        # Add country
        for point in viirs_data:
            point['country'] = country_name
        
        return {
            "status": "success",
            "location_info": {
                "city": city_name,
                "country": country_name,
                "lat": request.latitude,
                "lon": request.longitude,
                "radius_km": request.radius_km
            },
            "data": viirs_data,
            "metadata": {
                "baseline_year": request.start_year,
                "data_points": len(viirs_data),
                "data_source": "NOAA Earth Observation Group"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching data: {str(e)}"
        )


@app.get("/search")
def search_cities(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results")
):
    """
    Search for cities (autocomplete).
    
    Args:
        q: Search query (min 2 characters)
        limit: Maximum results
    
    Returns:
        {
            "status": "success",
            "query": str,
            "results": [...]
        }
    """
    try:
        # Check if query is coordinates
        coords = OSMService.parse_coordinate_string(q)
        
        if coords:
            lat, lon = coords
            location = osm_service.reverse_geocode(lat, lon)
            
            if location:
                return {
                    "status": "success",
                    "query": q,
                    "results": [location],
                    "type": "coordinates"
                }
        
        # Otherwise, search cities
        results = osm_service.search_cities(q, limit)
        
        return {
            "status": "success",
            "query": q,
            "results": results,
            "type": "city_search"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )


# Helper functions
def _validate_date_range(start: str, end: str) -> bool:
    """Validate that start date is before end date."""
    try:
        start_dt = datetime.strptime(start, "%Y-%m")
        end_dt = datetime.strptime(end, "%Y-%m")
        return start_dt <= end_dt
    except:
        return False


# Run server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=8000,
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )

