"""
Shared place resolution + VIIRS fetch for /viirs/city and /viirs/places.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from database import DatabaseManager
from osm_service import OSMService
from place_names import build_display_name, english_country, pick_english_name
from study_areas import resolve_study_area, study_area_to_city_info


def normalize_cached_viirs_rows(
    cached_rows: List[Dict[str, Any]],
    city_info: Dict[str, Any],
    min_cf_cvg: float,
) -> List[Dict[str, Any]]:
    return [
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


def _persist_city(db: DatabaseManager, query_city: str, city_info: Dict[str, Any]) -> None:
    try:
        db.add_city(
            {
                "name": query_city,
                "country": city_info["country"],
                "lat": city_info["lat"],
                "lon": city_info["lon"],
                "radius_km": city_info["radius_km"],
                "display_name": city_info.get("display_name", ""),
                "osm_id": str(city_info.get("osm_id") or ""),
                "place_type": city_info.get("place_type") or "city",
            }
        )
    except Exception as e:
        print(f"Warning: failed to write city to cache DB: {e}")


def resolve_place_info(
    query_city: str,
    query_country: Optional[str],
    db: DatabaseManager,
    osm_service: OSMService,
    *,
    acquire_network,
    release_network,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Resolve coordinates/metadata for a place.
    Returns (city_info, error_message).
    """
    study_site = resolve_study_area(query_city, query_country)
    if study_site:
        city_info = study_area_to_city_info(study_site, query_city)
        _persist_city(db, query_city, city_info)
        return city_info, None

    cached_city = db.get_city_by_name(query_city, query_country)
    if cached_city:
        return {
            "city": cached_city["name"],
            "country": english_country(cached_city["country"]),
            "lat": cached_city["latitude"],
            "lon": cached_city["longitude"],
            "radius_km": cached_city.get("radius_km") or 10.0,
            "display_name": cached_city.get("display_name") or build_display_name(
                cached_city["name"], cached_city["country"]
            ),
            "osm_id": cached_city.get("osm_id") or "",
            "place_type": cached_city.get("place_type") or "city",
        }, None

    if not acquire_network():
        return None, "Server is busy. Try again in a moment."
    try:
        raw = osm_service.geocode_city(query_city, query_country)
    finally:
        release_network()

    if not raw:
        return None, "Place not found"

    city_info = {
        "city": pick_english_name(query_city, raw.get("city")),
        "country": english_country(
            query_country if query_country else raw.get("country")
        ),
        "lat": raw["lat"],
        "lon": raw["lon"],
        "radius_km": raw.get("radius_km") or 10.0,
        "display_name": build_display_name(
            pick_english_name(query_city, raw.get("city")),
            query_country if query_country else raw.get("country"),
        ),
        "osm_id": str(raw.get("osm_id") or ""),
        "place_type": raw.get("place_type") or "city",
    }
    _persist_city(db, query_city, city_info)
    return city_info, None


def fetch_viirs_for_place(
    query_city: str,
    query_country: Optional[str],
    start_date: str,
    end_date: str,
    db: DatabaseManager,
    osm_service: OSMService,
    viirs_service,
    *,
    acquire_network,
    release_network,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], bool, Optional[str]]:
    """
    Returns (city_info, viirs_data, cache_hit, error_message).
    """
    city_info, err = resolve_place_info(
        query_city,
        query_country,
        db,
        osm_service,
        acquire_network=acquire_network,
        release_network=release_network,
    )
    if err:
        return None, [], False, err
    if not city_info:
        return None, [], False, "Place not found"

    cached_city = db.get_city_by_name(query_city, query_country or city_info["country"])
    min_cf_cvg = float(os.getenv("MIN_CF_CVG", "5"))
    viirs_data: List[Dict[str, Any]] = []

    if cached_city:
        cached_rows = db.get_viirs_data(
            city_id=cached_city["id"],
            start_date=start_date,
            end_date=end_date,
        )
        viirs_data = normalize_cached_viirs_rows(cached_rows, city_info, min_cf_cvg)

    if not viirs_data:
        if not acquire_network():
            return city_info, [], False, "Server is busy. Try again in a moment."
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
            release_network()

        try:
            city_id = db.add_city(
                {
                    "name": query_city,
                    "country": city_info["country"],
                    "lat": city_info["lat"],
                    "lon": city_info["lon"],
                    "radius_km": city_info["radius_km"],
                    "display_name": city_info.get("display_name", ""),
                    "osm_id": str(city_info.get("osm_id") or ""),
                    "place_type": city_info.get("place_type") or "city",
                }
            )
            db.add_viirs_data(city_id, viirs_data)
        except Exception as e:
            print(f"Warning: failed to write VIIRS cache: {e}")
        cache_hit = False
    else:
        cache_hit = True

    for point in viirs_data:
        point["country"] = city_info["country"]
        point["city"] = city_info["city"]

    return city_info, viirs_data, cache_hit, None
