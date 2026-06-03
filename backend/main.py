"""
FastAPI application for VIIRS nightlights data service.

Provides RESTful API endpoints for fetching and processing VIIRS data.
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
import uvicorn
from datetime import datetime
import os
import time
import hashlib
import threading
from pathlib import Path


def _load_dotenv() -> None:
    """Load backend/.env for local dev (gitignored; not used in friedso systemd)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

from noaa_viirs_service import NOAAVIIRSService
from gee_viirs_service import GEEVIIRSService, GEEServiceConfig
from osm_service import OSMService
from bias_correction import BiasCorrection
from database import DatabaseManager
from study_areas import (
    load_gulf_study_areas,
    load_strike_sites,
    resolve_study_area,
    study_area_to_city_info,
    sites_for_cluster_places,
)
from place_fetch import fetch_viirs_for_place


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
    allow_origins=[
        o.strip()
        for o in (
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:8080,http://localhost,http://localhost:8090,"
                "http://127.0.0.1:8090,http://127.0.0.1",
            ).split(",")
        )
        if o.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
_noaa_user = os.getenv("NOAA_EOG_USERNAME")
_noaa_pass = os.getenv("NOAA_EOG_PASSWORD")
_noaa_session = None
if _noaa_user and _noaa_pass:
    try:
        from noaa_auth import NOAAAuthenticator

        _noaa_session = NOAAAuthenticator(_noaa_user, _noaa_pass).get_authenticated_session()
    except Exception as e:
        print(f"Warning: NOAA authentication failed; continuing without session: {e}")

_source = os.getenv("VIIRS_SOURCE", "noaa").lower()
if _source == "gee":
    _gee_project = os.getenv("GEE_PROJECT_ID")
    if not _gee_project:
        raise RuntimeError("VIIRS_SOURCE=gee requires GEE_PROJECT_ID env var")
    viirs_service = GEEVIIRSService(GEEServiceConfig(project_id=_gee_project))
else:
    viirs_service = NOAAVIIRSService(session=_noaa_session)
osm_service = OSMService()
db = DatabaseManager(os.getenv("VIIRS_DB_PATH", "viirs_cache_local.db"))

DATA_SOURCE_LABEL = (
    "Google Earth Engine (NOAA VIIRS DNB Monthly V1 / VCMSLCFG)"
    if _source == "gee"
    else "NOAA Earth Observation Group"
)

HOTLIST_PATH = os.getenv("VIIRS_HOTLIST_PATH", "backend/data/hotlist.json")
CLUSTERS_PATH = os.getenv("VIIRS_CLUSTERS_PATH", "backend/data/clusters.json")
_hotlist_cache: Optional[Dict[str, Any]] = None
_clusters_cache: Optional[Dict[str, Any]] = None

MAX_INDIVIDUAL_PLACES = int(os.getenv("MAX_INDIVIDUAL_PLACES", "5"))
MAX_PLACES_PER_REQUEST = int(os.getenv("MAX_PLACES_PER_REQUEST", "12"))

# Overload guards (conservative defaults for a "tiny server")
MAX_INFLIGHT_NETWORK = int(os.getenv("MAX_INFLIGHT_NETWORK", "4"))
_network_sem = threading.BoundedSemaphore(MAX_INFLIGHT_NETWORK)

RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
_rl_lock = threading.Lock()
_rl_buckets: Dict[str, Tuple[int, float]] = {}  # ip -> (tokens, last_refill_ts)


def _client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return (req.client.host if req.client else "") or ""


def _ip_hash(ip: str) -> Optional[str]:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def _rate_limit_ok(ip: str) -> bool:
    if not ip:
        return True
    now = time.time()
    refill_rate_per_sec = RATE_LIMIT_PER_MIN / 60.0
    with _rl_lock:
        tokens, last = _rl_buckets.get(ip, (RATE_LIMIT_PER_MIN, now))
        elapsed = max(0.0, now - last)
        tokens = min(RATE_LIMIT_PER_MIN, tokens + int(elapsed * refill_rate_per_sec))
        if tokens <= 0:
            _rl_buckets[ip] = (tokens, now)
            return False
        _rl_buckets[ip] = (tokens - 1, now)
        return True


def _acquire_network_slot() -> bool:
    return _network_sem.acquire(blocking=False)


def _release_network_slot() -> None:
    try:
        _network_sem.release()
    except Exception:
        return


def _load_hotlist() -> Dict[str, Any]:
    global _hotlist_cache
    if _hotlist_cache is not None:
        return _hotlist_cache
    try:
        import json
        from pathlib import Path

        p = Path(HOTLIST_PATH)
        if not p.is_absolute():
            # Resolve relative to repo root when running from backend/
            repo_root = Path(__file__).resolve().parents[1]
            p = repo_root / p
        _hotlist_cache = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _hotlist_cache = {"version": 1, "count": 0, "places": []}
    return _hotlist_cache


def _load_clusters() -> Dict[str, Any]:
    global _clusters_cache
    if _clusters_cache is not None:
        return _clusters_cache
    try:
        import json
        from pathlib import Path

        p = Path(CLUSTERS_PATH)
        if not p.is_absolute():
            repo_root = Path(__file__).resolve().parents[1]
            p = repo_root / p
        _clusters_cache = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _clusters_cache = {"version": 1, "clusters": []}
    return _clusters_cache


def _place_display_name(place: Dict[str, Any]) -> str:
    name = str(place.get("name") or "").strip()
    country = str(place.get("country") or "").strip()
    admin1 = place.get("admin1")
    if admin1:
        return f"{name}, {admin1}, {country}"
    return f"{name}, {country}" if country else name


def _suggest_from_hotlist(query: str, limit: int = 10, country: Optional[str] = None) -> List[Dict]:
    """Prefix/contains match against preloaded hotlist (no network)."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []

    country_norm = (country or "").strip().lower()
    scored: List[Tuple[int, Dict]] = []

    for place in _load_hotlist().get("places") or []:
        name = str(place.get("name") or "")
        ctry = str(place.get("country") or "")
        admin1 = str(place.get("admin1") or "")
        name_l = name.lower()
        ctry_l = ctry.lower()
        admin_l = admin1.lower()
        display_l = _place_display_name(place).lower()

        if country_norm and country_norm not in ctry_l and country_norm not in display_l:
            continue

        score = 0
        if name_l.startswith(q):
            score += 20
        elif name_l.split()[0].startswith(q) if name_l else False:
            score += 15
        elif q in name_l:
            score += 8
        elif q in display_l:
            score += 4
        else:
            continue

        scored.append(
            (
                score,
                {
                    "city": name,
                    "country": ctry,
                    "admin1": admin1 or None,
                    "display_name": _place_display_name(place),
                    "lat": place.get("lat"),
                    "lon": place.get("lon"),
                    "source": "hotlist",
                },
            )
        )

    scored.sort(key=lambda t: (-t[0], t[1]["display_name"]))
    return [item for _, item in scored[:limit]]


# Request/Response Models
class CityRequest(BaseModel):
    city: str = Field(..., description="City name")
    country: Optional[str] = Field(None, description="Country name (optional)")
    start_month: int = Field(1, ge=1, le=12, description="Start month (1-12)")
    start_year: int = Field(2019, ge=2012, le=2100, description="Start year")
    end_month: int = Field(12, ge=1, le=12, description="End month (1-12)")
    end_year: int = Field(2024, ge=2012, le=2100, description="End year")


class MultiCityRequest(BaseModel):
    cities: List[str] = Field(..., max_length=5, description="List of city names (max 5)")
    start_month: int = Field(1, ge=1, le=12)
    start_year: int = Field(2019, ge=2012, le=2100)
    end_month: int = Field(12, ge=1, le=12)
    end_year: int = Field(2024, ge=2012, le=2100)


class PlaceName(BaseModel):
    city: str = Field(..., description="City name")
    country: Optional[str] = Field(None, description="Country name (optional)")


class MultiPlaceRequest(BaseModel):
    places: List[PlaceName] = Field(
        ...,
        max_length=MAX_PLACES_PER_REQUEST,
        description=f"List of places (max {MAX_PLACES_PER_REQUEST}; clusters may exceed 5)",
    )
    start_month: int = Field(1, ge=1, le=12)
    start_year: int = Field(2019, ge=2012, le=2100)
    end_month: int = Field(12, ge=1, le=12)
    end_year: int = Field(2024, ge=2012, le=2100)


class CoordinatesRequest(BaseModel):
    latitude: float = Field(..., ge=-65, le=75, description="Latitude (-65 to 75)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    radius_km: float = Field(10.0, gt=0, le=50, description="Radius in km")
    start_month: int = Field(1, ge=1, le=12)
    start_year: int = Field(2019, ge=2012, le=2100)
    end_month: int = Field(12, ge=1, le=12)
    end_year: int = Field(2024, ge=2012, le=2100)


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
        "data_source": DATA_SOURCE_LABEL,
        "endpoints": {
            "GET /": "API info",
            "GET /viirs/latest-available": "Get latest available data month",
            "POST /viirs/city": "Fetch VIIRS data for a city",
            "POST /viirs/cities": "Fetch VIIRS data for multiple cities",
            "POST /viirs/coordinates": "Fetch VIIRS data for coordinates",
            "GET /search": "City autocomplete search (hotlist + OSM fallback)",
            "GET /hotlist": "Preloaded place dictionary for client autocomplete",
            "GET /suggest": "Hotlist-only autocomplete (no network)",
            "GET /clusters": "Predefined place clusters (e.g. Ports of China)",
        }
    }


@app.get("/hotlist")
def get_hotlist():
    """
    Return the preloaded hotlist for instant client-side autocomplete.
    """
    data = _load_hotlist()
    places = []
    for p in data.get("places") or []:
        places.append(
            {
                "city": p.get("name"),
                "country": p.get("country"),
                "admin1": p.get("admin1"),
                "display_name": _place_display_name(p),
                "lat": p.get("lat"),
                "lon": p.get("lon"),
            }
        )
    return {
        "status": "success",
        "count": len(places),
        "places": places,
        "source": "hotlist",
    }


@app.get("/clusters")
def get_clusters():
    """Return predefined place clusters for one-click multi-port comparison."""
    data = _load_clusters()
    clusters_out = []
    for c in data.get("clusters") or []:
        places = c.get("places") or []
        clusters_out.append(
            {
                "id": c.get("id"),
                "label": c.get("label"),
                "description": c.get("description"),
                "aliases": c.get("aliases") or [],
                "section": c.get("section"),
                "human_curated": c.get("human_curated"),
                "radius_methodology": c.get("radius_methodology"),
                "countries_covered": c.get("countries_covered") or [],
                "default_start": c.get("default_start"),
                "baseline_year": c.get("baseline_year"),
                "lock_date_range": bool(c.get("lock_date_range")),
                "exempt_city_limit": bool(c.get("exempt_city_limit", True)),
                "place_count": len(places),
                "places": [
                    {
                        "city": p.get("city"),
                        "country": p.get("country"),
                        "display_name": f"{p.get('city')}, {p.get('country')}",
                    }
                    for p in places
                ],
                "study_sites": sites_for_cluster_places(places) if places else [],
            }
        )
    return {
        "status": "success",
        "max_individual_places": MAX_INDIVIDUAL_PLACES,
        "max_places_per_request": data.get("max_cluster_places") or MAX_PLACES_PER_REQUEST,
        "clusters": clusters_out,
    }


@app.get("/study-areas/gulf")
def get_gulf_study_areas():
    """Frozen Gulf/Hormuz port study areas (user-request)."""
    data = load_gulf_study_areas()
    return {"status": "success", **data}


@app.get("/study-areas/conflict-strikes")
def get_conflict_strike_areas():
    """Automated GDELT strike sites (may be empty until build script runs)."""
    data = load_strike_sites()
    return {"status": "success", **data}


@app.get("/suggest")
def suggest_places(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    country: Optional[str] = Query(None, description="Optional country filter"),
):
    """Hotlist autocomplete without calling OSM."""
    results = _suggest_from_hotlist(q, limit=limit, country=country)
    return {
        "status": "success",
        "query": q,
        "results": results,
        "type": "hotlist",
        "count": len(results),
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
def fetch_city_data(request: CityRequest, http_request: Request):
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
    started = time.time()
    cache_hit = False
    upstream = "cache"
    ip = _client_ip(http_request)
    if not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry soon.")
    try:
        # Validate date range
        start_date = f"{request.start_year}-{request.start_month:02d}"
        end_date = f"{request.end_year}-{request.end_month:02d}"
        
        if not _validate_date_range(start_date, end_date):
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Frozen study-area registry (Gulf ports, GDELT sites) — no geocoding invention
        study_site = resolve_study_area(request.city, request.country)
        if study_site:
            city_info = study_area_to_city_info(study_site, request.city)
            try:
                db.add_city(
                    {
                        "name": request.city,
                        "country": city_info["country"],
                        "lat": city_info["lat"],
                        "lon": city_info["lon"],
                        "radius_km": city_info["radius_km"],
                        "display_name": city_info.get("display_name", ""),
                        "osm_id": str(city_info.get("osm_id") or ""),
                        "place_type": city_info.get("place_type") or "study_area",
                    }
                )
            except Exception as e:
                print(f"Warning: failed to write study area to cache DB: {e}")
            cached_city = db.get_city_by_name(request.city, request.country)
        else:
            cached_city = db.get_city_by_name(request.city, request.country)

        city_info = None
        if cached_city:
            cache_hit = True
            city_info = {
                "city": cached_city["name"],
                "country": cached_city["country"],
                "lat": cached_city["latitude"],
                "lon": cached_city["longitude"],
                "radius_km": cached_city.get("radius_km") or 10.0,
                "display_name": cached_city.get("display_name") or "",
                "osm_id": cached_city.get("osm_id") or "",
                "place_type": cached_city.get("place_type") or "city",
            }
            if study_site:
                city_info["radius_rationale"] = study_site.get("radius_rationale") or study_site.get(
                    "registry_radius_methodology"
                )
                city_info["study_area_id"] = study_site.get("id")
                city_info["human_curated"] = study_site.get("human_curated")
        elif study_site:
            city_info = study_area_to_city_info(study_site, request.city)
        elif not study_site:
            upstream = "osm+viirs"
            if not _acquire_network_slot():
                raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
            # Geocode city (network)
            print(f"Geocoding: {request.city}, {request.country}")
            try:
                city_info = osm_service.geocode_city(request.city, request.country)
            finally:
                _release_network_slot()
            if not city_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"City '{request.city}' not found. Try different spelling or add country."
                )

            # Cache city record (best-effort) so future requests skip geocoding
            try:
                db.add_city(
                    {
                        # Store the user-provided query name to maximize future cache hits
                        "name": request.city,
                        "country": city_info["country"],
                        "lat": city_info["lat"],
                        "lon": city_info["lon"],
                        "radius_km": city_info["radius_km"],
                        "display_name": city_info.get("display_name", ""),
                        "osm_id": str(city_info.get("osm_id", "")),
                        "place_type": city_info.get("place_type", "city"),
                    }
                )
            except Exception as e:
                print(f"Warning: failed to write city to cache DB: {e}")

            cached_city = db.get_city_by_name(city_info["city"], city_info["country"])

        viirs_data = []
        if cached_city:
            cached_rows = db.get_viirs_data(
                city_id=cached_city["id"],
                start_date=start_date,
                end_date=end_date,
            )
            # Normalize cache rows to API schema expected by frontend
            min_cf_cvg = float(os.getenv("MIN_CF_CVG", "5"))
            viirs_data = [
                {
                    "date": r["date"],
                    "city": r.get("city_name") or city_info["city"],
                    "country": r.get("country") or city_info["country"],
                    "latitude": r.get("latitude") or city_info["lat"],
                    "longitude": r.get("longitude") or city_info["lon"],
                    "radiance": None if (r.get("cloud_free_coverage") is not None and r.get("cloud_free_coverage") < min_cf_cvg) else r["radiance"],
                    "radiance_corrected": None if (r.get("cloud_free_coverage") is not None and r.get("cloud_free_coverage") < min_cf_cvg) else r["radiance_corrected"],
                    "cloud_free_coverage": r.get("cloud_free_coverage"),
                    "data_quality": "low" if (r.get("cloud_free_coverage") is not None and r.get("cloud_free_coverage") < min_cf_cvg) else "ok",
                }
                for r in cached_rows
            ]

        if not viirs_data:
            cache_hit = False
            upstream = "viirs"
            if not _acquire_network_slot():
                raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
            print(f"Fetching VIIRS data from {DATA_SOURCE_LABEL} (cache miss)...")
            try:
                viirs_data = viirs_service.fetch_viirs_for_city(
                    city_name=city_info["city"],
                    lat=city_info["lat"],
                    lon=city_info["lon"],
                    radius_km=city_info["radius_km"],
                    start_date=start_date,
                    end_date=end_date,
                )
            finally:
                _release_network_slot()

            # Persist to cache DB (best-effort)
            try:
                city_id = db.add_city(
                    {
                        # Store the user-provided query name to maximize future cache hits
                        "name": request.city,
                        "country": city_info["country"],
                        "lat": city_info["lat"],
                        "lon": city_info["lon"],
                        "radius_km": city_info["radius_km"],
                        "display_name": city_info.get("display_name", ""),
                        "osm_id": str(city_info.get("osm_id", "")),
                        "place_type": city_info.get("place_type", "city"),
                    }
                )
                db.add_viirs_data(city_id, viirs_data)
            except Exception as e:
                print(f"Warning: failed to write cache DB: {e}")
        
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
                "data_source": DATA_SOURCE_LABEL,
                "bias_correction": "Elvidge et al. (2021)",
                "processing": "On-the-fly",
                "min_cf_cvg": float(os.getenv("MIN_CF_CVG", "5")),
                "missing_data_policy": "Months with cloud_free_coverage < MIN_CF_CVG are returned as null radiance to avoid misleading zeros."
            },
            "status_context": {
                "cache_hit": bool(cache_hit),
                "network_used": (not cache_hit),
                "upstream": upstream if (not cache_hit) else "sqlite",
                "latency_ms": (time.time() - started) * 1000.0,
            },
        }
    
    except HTTPException as he:
        try:
            db.add_query_log(
                {
                    "event_type": "viirs_city",
                    "query_text": request.city,
                    "selected_name": request.city,
                    "selected_country": request.country,
                    "ip_hash": _ip_hash(ip),
                    "cache_hit": cache_hit,
                    "upstream": upstream,
                    "latency_ms": (time.time() - started) * 1000.0,
                    "status": "error",
                    "error_code": f"http_{he.status_code}",
                }
            )
        except Exception:
            pass
        raise
    except Exception as e:
        # Best-effort query log
        try:
            db.add_query_log(
                {
                    "event_type": "viirs_city",
                    "query_text": request.city,
                    "selected_name": request.city,
                    "selected_country": request.country,
                    "ip_hash": _ip_hash(ip),
                    "cache_hit": cache_hit,
                    "upstream": upstream,
                    "latency_ms": (time.time() - started) * 1000.0,
                    "status": "error",
                    "error_code": "unhandled_exception",
                }
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching data: {str(e)}"
        )


@app.post("/viirs/cities")
def fetch_multi_city_data(request: MultiCityRequest, http_request: Request):
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
    
    started = time.time()
    for city_name in request.cities:
        try:
            # Cache-first: try DB lookup first
            cached_city = db.get_city_by_name(city_name, None)
            city_info = None
            viirs_data = []

            if cached_city:
                city_info = {
                    "city": cached_city["name"],
                    "country": cached_city["country"],
                    "lat": cached_city["latitude"],
                    "lon": cached_city["longitude"],
                    "radius_km": cached_city.get("radius_km") or 10.0,
                    "display_name": cached_city.get("display_name") or "",
                    "osm_id": cached_city.get("osm_id") or "",
                    "place_type": cached_city.get("place_type") or "city",
                }
                cached_rows = db.get_viirs_data(
                    city_id=cached_city["id"],
                    start_date=start_date,
                    end_date=end_date,
                )
                min_cf_cvg = float(os.getenv("MIN_CF_CVG", "5"))
                viirs_data = [
                    {
                        "date": r["date"],
                        "city": r.get("city_name") or city_info["city"],
                        "country": r.get("country") or city_info["country"],
                        "latitude": r.get("latitude") or city_info["lat"],
                        "longitude": r.get("longitude") or city_info["lon"],
                        "radiance": None
                        if (r.get("cloud_free_coverage") is not None and r.get("cloud_free_coverage") < min_cf_cvg)
                        else r["radiance"],
                        "radiance_corrected": None
                        if (r.get("cloud_free_coverage") is not None and r.get("cloud_free_coverage") < min_cf_cvg)
                        else r["radiance_corrected"],
                        "cloud_free_coverage": r.get("cloud_free_coverage"),
                        "data_quality": "low"
                        if (r.get("cloud_free_coverage") is not None and r.get("cloud_free_coverage") < min_cf_cvg)
                        else "ok",
                    }
                    for r in cached_rows
                ]

            if not viirs_data:
                # Geocode only if DB doesn't already have this city
                city_info = osm_service.geocode_city(city_name)
                if not city_info:
                    errors.append({"city": city_name, "error": "City not found"})
                    continue

                viirs_data = viirs_service.fetch_viirs_for_city(
                    city_name=city_info["city"],
                    lat=city_info["lat"],
                    lon=city_info["lon"],
                    radius_km=city_info["radius_km"],
                    start_date=start_date,
                    end_date=end_date,
                )

                # Persist to cache DB (best-effort)
                try:
                    city_id = db.add_city(
                        {
                            # Store the user-provided query name to maximize future cache hits
                            "name": city_name,
                            "country": city_info["country"],
                            "lat": city_info["lat"],
                            "lon": city_info["lon"],
                            "radius_km": city_info["radius_km"],
                            "display_name": city_info.get("display_name", ""),
                            "osm_id": str(city_info.get("osm_id", "")),
                            "place_type": city_info.get("place_type", "city"),
                        }
                    )
                    db.add_viirs_data(city_id, viirs_data)
                except Exception as e:
                    print(f"Warning: failed to write cache DB: {e}")

            # Ensure country on points (frontend expects it)
            for point in viirs_data:
                point["country"] = city_info["country"]

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
            "total_data_points": len(all_data),
            "data_source": DATA_SOURCE_LABEL,
            "bias_correction": "Elvidge et al. (2021)",
            "min_cf_cvg": float(os.getenv("MIN_CF_CVG", "5")),
            "missing_data_policy": "Months with cloud_free_coverage < MIN_CF_CVG are returned as null radiance to avoid misleading zeros."
        },
        "status_context": {
            "cache_mixed": True,
            "network_used": any("error" not in (e or {}) for e in (errors or [])),
            "latency_ms": (time.time() - started) * 1000.0,
        },
    }


@app.post("/viirs/places")
def fetch_multi_place_data(request: MultiPlaceRequest, http_request: Request):
    """
    Multi-place endpoint that supports country disambiguation for each entry.
    Preferred for ambiguous names (e.g., Gaza).
    """
    max_places = MAX_PLACES_PER_REQUEST
    if len(request.places) > max_places:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_places} places per request",
        )

    started = time.time()
    ip = _client_ip(http_request)
    if not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry soon.")

    start_date = f"{request.start_year}-{request.start_month:02d}"
    end_date = f"{request.end_year}-{request.end_month:02d}"
    if not _validate_date_range(start_date, end_date):
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    results = []
    errors = []
    all_data = []

    for place in request.places:
        city_name = place.city
        country_name = place.country
        try:
            city_info, viirs_data, _cache_hit, err = fetch_viirs_for_place(
                city_name,
                country_name,
                start_date,
                end_date,
                db,
                osm_service,
                viirs_service,
                acquire_network=_acquire_network_slot,
                release_network=_release_network_slot,
            )
            if err:
                errors.append({"city": city_name, "country": country_name, "error": err})
                continue
            if not city_info:
                errors.append({"city": city_name, "country": country_name, "error": "Place not found"})
                continue

            results.append(city_info)
            all_data.extend(viirs_data)
        except Exception as e:
            errors.append({"city": city_name, "country": country_name, "error": str(e)})

    return {
        "status": "success" if results else "error",
        "cities": results,
        "data": all_data,
        "errors": errors if errors else None,
        "metadata": {
            "cities_processed": len(results),
            "cities_failed": len(errors),
            "total_data_points": len(all_data),
            "data_source": DATA_SOURCE_LABEL,
            "bias_correction": "Elvidge et al. (2021)",
            "min_cf_cvg": float(os.getenv("MIN_CF_CVG", "5")),
            "missing_data_policy": "Months with cloud_free_coverage < MIN_CF_CVG are returned as null radiance to avoid misleading zeros.",
        },
        "status_context": {
            "cache_mixed": True,
            "network_used": True,
            "latency_ms": (time.time() - started) * 1000.0,
        },
    }


@app.post("/viirs/coordinates")
def fetch_coordinates_data(request: CoordinatesRequest, http_request: Request):
    """
    Fetch VIIRS data for specific coordinates.
    
    Args:
        request: Coordinates request
    
    Returns:
        Similar to /viirs/city endpoint
    """
    started = time.time()
    upstream = "viirs"
    ip = _client_ip(http_request)
    if not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry soon.")
    try:
        start_date = f"{request.start_year}-{request.start_month:02d}"
        end_date = f"{request.end_year}-{request.end_month:02d}"
        
        if not _validate_date_range(start_date, end_date):
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        upstream = "osm+viirs"
        if not _acquire_network_slot():
            raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
        try:
            # Reverse geocode to get location name
            location_info = osm_service.reverse_geocode(
                request.latitude,
                request.longitude
            )
        finally:
            _release_network_slot()
        
        city_name = location_info['city'] if location_info else "Custom Location"
        country_name = location_info['country'] if location_info else "Unknown"
        
        if not _acquire_network_slot():
            raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
        try:
            # Fetch VIIRS data
            viirs_data = viirs_service.fetch_viirs_for_city(
                city_name=city_name,
                lat=request.latitude,
                lon=request.longitude,
                radius_km=request.radius_km,
                start_date=start_date,
                end_date=end_date
            )
        finally:
            _release_network_slot()
        
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
                "data_source": DATA_SOURCE_LABEL,
                "bias_correction": "Elvidge et al. (2021)",
                "min_cf_cvg": float(os.getenv("MIN_CF_CVG", "5")),
                "missing_data_policy": "Months with cloud_free_coverage < MIN_CF_CVG are returned as null radiance to avoid misleading zeros."
            },
            "status_context": {
                "cache_hit": False,
                "network_used": True,
                "upstream": upstream,
                "latency_ms": (time.time() - started) * 1000.0,
            },
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
    http_request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
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
    started = time.time()
    ip = _client_ip(http_request) if http_request is not None else ""
    # Note: /search is frequently called while typing; keep rate limit generous.
    if ip and not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry soon.")
    try:
        # Check if query is coordinates
        coords = OSMService.parse_coordinate_string(q)
        
        # Tier 1: hotlist (instant, no network)
        hotlist_hits = _suggest_from_hotlist(q, limit=limit)
        if hotlist_hits:
            try:
                db.add_query_log(
                    {
                        "event_type": "search_hotlist",
                        "query_text": q,
                        "status": "ok",
                        "upstream": "hotlist",
                        "latency_ms": (time.time() - started) * 1000.0,
                    }
                )
            except Exception:
                pass
            return {
                "status": "success",
                "query": q,
                "results": hotlist_hits,
                "type": "hotlist",
            }

        if coords:
            lat, lon = coords
            if not _acquire_network_slot():
                raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
            try:
                location = osm_service.reverse_geocode(lat, lon)
            finally:
                _release_network_slot()
            
            if location:
                # Log coordinate search
                try:
                    db.add_query_log(
                        {
                            "event_type": "search_coordinates",
                            "query_text": q,
                            "status": "ok",
                            "upstream": "osm_reverse",
                            "latency_ms": (time.time() - started) * 1000.0,
                        }
                    )
                except Exception:
                    pass
                return {
                    "status": "success",
                    "query": q,
                    "results": [location],
                    "type": "coordinates"
                }
        
        # Otherwise, search cities
        if not _acquire_network_slot():
            raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
        try:
            results = osm_service.search_cities(q, limit)
        finally:
            _release_network_slot()

        # Log search query
        try:
            db.add_query_log(
                {
                    "event_type": "search_text",
                    "query_text": q,
                    "status": "ok",
                    "upstream": "osm_search",
                    "latency_ms": (time.time() - started) * 1000.0,
                }
            )
        except Exception:
            pass
        
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

