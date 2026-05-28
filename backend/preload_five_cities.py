#!/usr/bin/env python3
"""
Preload/cache VIIRS data for the 5 UI cities into a local SQLite DB.

This is meant for local research/dev convenience (not committed data).

Usage:
  export NOAA_EOG_USERNAME="..."
  export NOAA_EOG_PASSWORD="..."
  export VIIRS_DB_PATH="viirs_cache_local.db"
  python3 backend/preload_five_cities.py --start 2024-01 --end 2024-12
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime

from database import DatabaseManager
from osm_service import OSMService

# Data sources
from noaa_viirs_service import NOAAVIIRSService
from gee_viirs_service import GEEVIIRSService, GEEServiceConfig
from noaa_auth import NOAAAuthenticator


FIVE_CITIES = [
    ("Mumbai", "India"),
    ("Delhi", "India"),
    ("Bengaluru", "India"),
    ("Chennai", "India"),
    ("Tiruppur", "India"),
]

def _ym_to_dt(ym: str) -> datetime:
    return datetime.strptime(ym, "%Y-%m")


def _dt_to_ym(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _add_months(dt: datetime, months: int) -> datetime:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=y, month=m)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preload VIIRS cache for 5 cities")
    parser.add_argument("--start", help="Start date YYYY-MM (optional if --recent-months is used)")
    parser.add_argument("--end", help="End date YYYY-MM (optional; defaults to latest available)")
    parser.add_argument(
        "--recent-months",
        type=int,
        help="Preload the most recent N months ending at latest available (recommended)",
    )
    args = parser.parse_args()

    db_path = os.getenv("VIIRS_DB_PATH", "viirs_cache_local.db")
    db = DatabaseManager(db_path)

    source = os.getenv("VIIRS_SOURCE", "noaa").lower()
    if source == "gee":
        project_id = os.getenv("GEE_PROJECT_ID")
        if not project_id:
            raise RuntimeError("VIIRS_SOURCE=gee requires GEE_PROJECT_ID")
        viirs = GEEVIIRSService(GEEServiceConfig(project_id=project_id))
    else:
        user = os.getenv("NOAA_EOG_USERNAME")
        pwd = os.getenv("NOAA_EOG_PASSWORD")
        session = None
        if user and pwd:
            session = NOAAAuthenticator(user, pwd).get_authenticated_session()
        viirs = NOAAVIIRSService(session=session)

    # Resolve date range
    latest = viirs.get_latest_available_month()
    latest_ym = f"{latest['year']}-{latest['month']:02d}"

    if args.recent_months:
        end_ym = latest_ym
        start_dt = _add_months(_ym_to_dt(end_ym), -(args.recent_months - 1))
        start_ym = _dt_to_ym(start_dt)
    else:
        if not args.start:
            raise SystemExit("Provide --start/--end or use --recent-months")
        start_ym = args.start
        end_ym = args.end or latest_ym

    osm = OSMService()

    for city, country in FIVE_CITIES:
        print(f"\n== Preloading {city}, {country} ==")
        city_info = osm.geocode_city(city, country)
        if not city_info:
            print("  !! Could not geocode; skipping")
            continue

        points = viirs.fetch_viirs_for_city(
            city_name=city_info["city"],
            lat=city_info["lat"],
            lon=city_info["lon"],
            radius_km=city_info["radius_km"],
            start_date=start_ym,
            end_date=end_ym,
        )
        print(f"  Downloaded points: {len(points)}")

        if not points:
            continue

        city_id = db.add_city(
            {
                "name": city_info["city"],
                "country": city_info["country"],
                "lat": city_info["lat"],
                "lon": city_info["lon"],
                "radius_km": city_info["radius_km"],
                "display_name": city_info.get("display_name", ""),
                "osm_id": str(city_info.get("osm_id", "")),
                "place_type": city_info.get("place_type", "city"),
            }
        )
        db.add_viirs_data(city_id, points)
        print("  Cached to DB.")

    print(f"\nDone. Cache DB: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

