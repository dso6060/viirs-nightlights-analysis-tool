#!/usr/bin/env python3
"""
Preload VIIRS monthly series for Gulf study areas + GDELT strike sites.

Uses coordinates/radii from JSON only (no geocoding).

Per-site date windows:
  - Gulf ports: registry default_start (or --gulf-start) → end
  - GDELT strikes: event_date − months_before → end

Usage:
  export VIIRS_SOURCE=gee
  export GEE_PROJECT_ID=...
  export GOOGLE_APPLICATION_CREDENTIALS=...
  export VIIRS_DB_PATH=viirs_cache_local.db

  python3 scripts/preload_study_areas.py --gulf-start 2025-10 --end latest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from database import DatabaseManager  # noqa: E402
from gee_viirs_service import GEEVIIRSService, GEEServiceConfig  # noqa: E402
from noaa_viirs_service import NOAAVIIRSService  # noqa: E402


def load_sites(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not path.is_file():
        return [], {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("sites") or []), data


def resolve_end(end: str, viirs_service) -> str:
    if end != "latest":
        return end
    latest = viirs_service.get_latest_available_month()
    return f"{latest['year']}-{latest['month']:02d}"


def _parse_ym(s: str) -> datetime:
    y, m = s.split("-")[:2]
    return datetime(int(y), int(m), 1)


def _ym(dt: datetime) -> str:
    return f"{dt.year}-{dt.month:02d}"


def _add_months(dt: datetime, months: int) -> datetime:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=y, month=m)


def site_window(
    site: Dict[str, Any],
    *,
    gulf_start: str,
    strike_months_before: int,
    global_start: str,
    end: str,
) -> Tuple[str, str]:
    kind = site.get("source_kind")
    if kind == "gdelt_strike":
        event_date = (site.get("event_date") or "")[:10]
        if event_date and len(event_date) >= 7:
            try:
                ev = datetime(int(event_date[:4]), int(event_date[5:7]), 1)
                start_dt = _add_months(ev, -strike_months_before)
                return _ym(start_dt), end
            except ValueError:
                pass
        return global_start, end

    if kind == "gulf_port":
        reg_start = site.get("default_start") or gulf_start
        return str(reg_start), end

    return global_start, end


def preload_site(
    db: DatabaseManager,
    viirs_service,
    site: Dict[str, Any],
    start: str,
    end: str,
) -> int:
    name = str(site.get("label") or site.get("id"))
    country = str(site["country"])
    lat = float(site["lat"])
    lon = float(site["lon"])
    radius_km = float(site["radius_km"])

    city_id = db.add_city(
        {
            "name": name,
            "country": country,
            "lat": lat,
            "lon": lon,
            "radius_km": radius_km,
            "display_name": f"{name}, {country}",
            "osm_id": str(site.get("id") or ""),
            "place_type": site.get("source_kind") or "study_area",
        }
    )

    rows = viirs_service.fetch_viirs_for_city(
        city_name=name,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        start_date=start,
        end_date=end,
    )
    viirs_payload = [
        {
            "date": r["date"],
            "radiance": r.get("radiance"),
            "radiance_corrected": r.get("radiance_corrected"),
            "cloud_free_coverage": r.get("cloud_free_coverage"),
        }
        for r in rows
    ]
    return db.add_viirs_data(city_id, viirs_payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2021-01", help="Fallback start for strikes without event_date")
    parser.add_argument("--gulf-start", default=None, help="Gulf ports start YYYY-MM (default: registry default_start)")
    parser.add_argument("--end", default="latest")
    parser.add_argument("--months-before-impact", type=int, default=6, help="GDELT strike preload window before event_date")
    parser.add_argument("--dataset", choices=["all", "gulf", "strikes"], default="all")
    args = parser.parse_args()

    source = os.getenv("VIIRS_SOURCE", "noaa").lower()
    if source == "gee":
        project = os.getenv("GEE_PROJECT_ID")
        if not project:
            print("GEE_PROJECT_ID required for VIIRS_SOURCE=gee", file=sys.stderr)
            sys.exit(1)
        viirs = GEEVIIRSService(GEEServiceConfig(project_id=project))
    else:
        viirs = NOAAVIIRSService()

    db_path = os.getenv("VIIRS_DB_PATH", str(ROOT / "backend" / "viirs_cache_local.db"))
    db = DatabaseManager(db_path)
    end = resolve_end(args.end, viirs)

    gulf_registry: Dict[str, Any] = {}
    sites: List[Dict[str, Any]] = []
    if args.dataset in ("all", "gulf"):
        gulf_sites, gulf_registry = load_sites(ROOT / "backend" / "data" / "gulf_study_areas.json")
        for s in gulf_sites:
            s = dict(s)
            s["source_kind"] = "gulf_port"
            sites.append(s)
    if args.dataset in ("all", "strikes"):
        for s in load_sites(ROOT / "backend" / "data" / "conflict_strike_sites.json")[0]:
            s = dict(s)
            s["source_kind"] = "gdelt_strike"
            sites.append(s)

    if not sites:
        print("No sites to preload.", file=sys.stderr)
        sys.exit(1)

    gulf_start = args.gulf_start or gulf_registry.get("default_start") or "2026-01"

    print(f"Preloading {len(sites)} sites via {source} (end={end})")
    for i, site in enumerate(sites, 1):
        label = site.get("label") or site.get("id")
        start, site_end = site_window(
            site,
            gulf_start=str(gulf_start),
            strike_months_before=args.months_before_impact,
            global_start=args.start,
            end=end,
        )
        try:
            n = preload_site(db, viirs, site, start, site_end)
            print(f"  [{i}/{len(sites)}] {label}: {start} → {site_end} ({n} months)")
        except Exception as e:
            print(f"  [{i}/{len(sites)}] {label}: FAILED {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
