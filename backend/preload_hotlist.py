#!/usr/bin/env python3
"""
Preload/cache VIIRS monthly series for a hotlist of places into SQLite.

Design goals:
- Prefer *no* Nominatim/geocoding during preload: hotlist contains coordinates.
- Use VIIRS_SOURCE=gee (recommended) for stable, small-area reductions.
- Write into the existing SQLite schema (cities + viirs_data).

Usage (GEE recommended):
  export VIIRS_SOURCE=gee
  export GEE_PROJECT_ID="..."
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service_account.json"
  export VIIRS_DB_PATH="viirs_cache_local.db"

  python3 backend/preload_hotlist.py \
    --hotlist backend/data/hotlist.json \
    --start 2019-01 \
    --end latest \
    --limit 800
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import DatabaseManager
from gee_viirs_service import GEEVIIRSService, GEEServiceConfig
from noaa_viirs_service import NOAAVIIRSService
from noaa_auth import NOAAAuthenticator


@dataclass(frozen=True)
class HotlistPlace:
    name: str
    country: str
    lat: float
    lon: float
    admin1: Optional[str] = None
    place_type: str = "city"
    radius_km: Optional[float] = None
    display_name: Optional[str] = None
    osm_id: Optional[str] = None


def _dt_to_ym(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _add_months(dt: datetime, months: int) -> datetime:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=y, month=m)


def load_hotlist(path: Path) -> List[HotlistPlace]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    places = payload.get("places") or []
    out: List[HotlistPlace] = []
    for p in places:
        out.append(
            HotlistPlace(
                name=str(p["name"]),
                country=str(p["country"]),
                lat=float(p["lat"]),
                lon=float(p["lon"]),
                admin1=str(p["admin1"]) if p.get("admin1") else None,
                place_type=str(p.get("place_type") or "city"),
                radius_km=float(p["radius_km"]) if p.get("radius_km") is not None else None,
                display_name=f"{p.get('name')}, {p.get('admin1') + ', ' if p.get('admin1') else ''}{p.get('country')}",
                osm_id=str(p.get("osm_id")) if p.get("osm_id") else None,
            )
        )
    return out


def get_viirs_service():
    source = os.getenv("VIIRS_SOURCE", "noaa").lower()
    if source == "gee":
        project_id = os.getenv("GEE_PROJECT_ID")
        if not project_id:
            raise RuntimeError("VIIRS_SOURCE=gee requires GEE_PROJECT_ID")
        return GEEVIIRSService(GEEServiceConfig(project_id=project_id))

    user = os.getenv("NOAA_EOG_USERNAME")
    pwd = os.getenv("NOAA_EOG_PASSWORD")
    session = None
    if user and pwd:
        session = NOAAAuthenticator(user, pwd).get_authenticated_session()
    return NOAAVIIRSService(session=session)


def main() -> int:
    ap = argparse.ArgumentParser(description="Preload VIIRS cache for hotlist places")
    ap.add_argument("--hotlist", default="backend/data/hotlist.json", help="Path to hotlist.json")
    ap.add_argument("--start", default="2019-01", help="Start YYYY-MM")
    ap.add_argument("--end", default="latest", help="End YYYY-MM or 'latest'")
    ap.add_argument("--limit", type=int, default=800, help="Max places to preload")
    ap.add_argument("--recent-months", type=int, help="Override start/end: preload last N months to latest")
    args = ap.parse_args()

    db_path = os.getenv("VIIRS_DB_PATH", "viirs_cache_local.db")
    db = DatabaseManager(db_path)
    viirs = get_viirs_service()

    latest = viirs.get_latest_available_month()
    latest_ym = f"{latest['year']}-{latest['month']:02d}"

    if args.recent_months:
        end_ym = latest_ym
        start_dt = _add_months(datetime.strptime(end_ym, "%Y-%m"), -(args.recent_months - 1))
        start_ym = _dt_to_ym(start_dt)
    else:
        start_ym = args.start
        end_ym = latest_ym if str(args.end).lower() == "latest" else args.end

    hotlist_path = Path(args.hotlist)
    places = load_hotlist(hotlist_path)[: args.limit]

    print(f"DB: {db_path}")
    print(f"Hotlist: {hotlist_path} (places={len(places)})")
    print(f"Range: {start_ym} → {end_ym} (latest={latest_ym})")
    print(f"Source: {os.getenv('VIIRS_SOURCE', 'noaa')}")

    for idx, p in enumerate(places, start=1):
        try:
            radius_km = p.radius_km or 10.0
            print(f"\n[{idx}/{len(places)}] {p.name}, {p.country} ({p.lat:.4f},{p.lon:.4f}) r={radius_km}km")

            points = viirs.fetch_viirs_for_city(
                city_name=p.name,
                lat=p.lat,
                lon=p.lon,
                radius_km=radius_km,
                start_date=start_ym,
                end_date=end_ym,
            )
            print(f"  points: {len(points)}")
            if not points:
                continue

            city_id = db.add_city(
                {
                    "name": p.name,
                    "country": p.country,
                    "lat": p.lat,
                    "lon": p.lon,
                    "radius_km": radius_km,
                    "display_name": p.display_name or "",
                    "osm_id": p.osm_id or "",
                    "place_type": p.place_type or "city",
                }
            )
            db.add_viirs_data(city_id, points)
            print("  cached: ok")
        except Exception as e:
            print(f"  cached: failed ({e})")
            continue

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

