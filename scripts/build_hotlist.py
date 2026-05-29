#!/usr/bin/env python3
"""
Build a reproducible hotlist (~800 places) for fast autocomplete + preloading.

Sources (lightweight):
- Project curated list: backend/cities_data.py
- Manual additions: India capitals + requested industrial clusters + major ports/chokepoints
- Natural Earth populated places (GeoJSON) for global coverage (no heavy GIS deps)

Output:
  backend/data/hotlist.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "backend" / "data" / "hotlist.json"

NE_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_10m_populated_places_simple.geojson"
)


@dataclass(frozen=True)
class Place:
    name: str
    country: str
    lat: float
    lon: float
    # Optional fields used for UI clarity + preloading behavior
    admin1: Optional[str] = None
    place_type: str = "city"  # city|port_city|industrial|capital|chokepoint|metro
    radius_km: Optional[float] = None
    tags: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    source: str = "unknown"

    def key(self) -> Tuple[str, str]:
        return (self.name.strip().lower(), self.country.strip().lower())


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _as_place(d: Dict[str, Any], source: str) -> Place:
    return Place(
        name=str(d["name"]).strip(),
        country=str(d["country"]).strip(),
        lat=float(d["lat"]),
        lon=float(d["lon"]),
        radius_km=float(d["radius_km"]) if d.get("radius_km") is not None else None,
        place_type=str(d.get("place_type") or d.get("category") or "city"),
        tags=list(d.get("tags") or []),
        aliases=list(d.get("aliases") or []),
        admin1=str(d["admin1"]).strip() if d.get("admin1") else None,
        source=source,
    )


def load_project_cities() -> List[Place]:
    # Import the existing curated list
    import importlib.util

    module_path = ROOT / "backend" / "cities_data.py"
    spec = importlib.util.spec_from_file_location("cities_data", module_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    cities = getattr(mod, "CITIES_DATA", [])
    out: List[Place] = []
    for c in cities:
        out.append(
            Place(
                name=c["name"],
                country=c["country"],
                lat=float(c["lat"]),
                lon=float(c["lon"]),
                radius_km=float(c.get("radius_km")) if c.get("radius_km") is not None else None,
                place_type=str(c.get("category") or "city"),
                tags=[str(c.get("category") or "city")],
                source="project_cities_data",
            )
        )
    return out


def manual_additions() -> List[Place]:
    # India state/UT capitals + a few key industrial clusters + requested port cities.
    # (Coordinates intentionally not hard-coded here except where already in project list;
    # we’ll rely on Natural Earth + project list for most coords.)
    # These are added as "alias-only" seeds to ensure search visibility; coords are filled
    # from Natural Earth later when possible.
    seeds: List[Dict[str, Any]] = []

    # India capitals (state + UT capitals). Country kept as "India".
    india_capitals = [
        "Amaravati",
        "Itanagar",
        "Dispur",
        "Patna",
        "Raipur",
        "Panaji",
        "Gandhinagar",
        "Chandigarh",
        "Shimla",
        "Ranchi",
        "Bengaluru",
        "Thiruvananthapuram",
        "Bhopal",
        "Mumbai",
        "Imphal",
        "Shillong",
        "Aizawl",
        "Kohima",
        "Bhubaneswar",
        "Chandigarh",
        "Jaipur",
        "Gangtok",
        "Chennai",
        "Hyderabad",
        "Agartala",
        "Lucknow",
        "Dehradun",
        "Kolkata",
        "New Delhi",
        "Puducherry",
        "Srinagar",
        "Jammu",
        "Leh",
        "Kavaratti",
        "Port Blair",
        "Daman",
        "Silvassa",
    ]

    for n in india_capitals:
        seeds.append({"name": n, "country": "India", "place_type": "capital", "tags": ["india_capital"]})

    # Requested industrial clusters (ensure present for autocomplete)
    industrial = ["Tiruppur", "Coimbatore", "Ludhiana", "Jalandhar"]
    for n in industrial:
        seeds.append({"name": n, "country": "India", "place_type": "industrial", "tags": ["industrial_cluster"]})

    # A few explicit ambiguous names with alias seeds to improve disambiguation labels
    seeds.append({"name": "Gaza", "country": "Palestine", "place_type": "city", "tags": ["ambiguous_name"], "aliases": ["Gaza City"]})

    # Port metros (labels only; coords will come from project list / Natural Earth)
    ports = [
        ("Los Angeles", "United States"),
        ("Long Beach", "United States"),
        ("New York", "United States"),
        ("Norfolk", "United States"),
        ("Savannah", "United States"),
        ("Charleston", "United States"),
        ("Miami", "United States"),
        ("Houston", "United States"),
        ("New Orleans", "United States"),
        ("Jacksonville", "United States"),
        ("Seattle", "United States"),
        ("Shanghai", "China"),
        ("Ningbo", "China"),
        ("Shenzhen", "China"),
        ("Guangzhou", "China"),
        ("Qingdao", "China"),
        ("Tianjin", "China"),
        ("Xiamen", "China"),
        ("Dalian", "China"),
        ("Hong Kong", "Hong Kong"),
        ("Mumbai", "India"),
        ("Chennai", "India"),
        ("Kolkata", "India"),
        ("Visakhapatnam", "India"),
        ("Kochi", "India"),
        ("Piraeus", "Greece"),
        ("Thessaloniki", "Greece"),
        ("Dubai", "United Arab Emirates"),
        ("Abu Dhabi", "United Arab Emirates"),
        ("Fujairah", "United Arab Emirates"),
        ("Muscat", "Oman"),
        ("Bandar Abbas", "Iran"),
        ("Doha", "Qatar"),
        ("Manama", "Bahrain"),
        ("Kuwait City", "Kuwait"),
    ]
    for name, country in ports:
        seeds.append({"name": name, "country": country, "place_type": "port_city", "tags": ["port_city"]})

    out: List[Place] = []
    for s in seeds:
        # Set lat/lon placeholders; will be filled from Natural Earth match later.
        out.append(
            Place(
                name=s["name"],
                country=s["country"],
                lat=0.0,
                lon=0.0,
                admin1=None,
                place_type=s.get("place_type", "city"),
                radius_km=None,
                tags=list(s.get("tags") or []),
                aliases=list(s.get("aliases") or []),
                source="manual_seed",
            )
        )
    return out


def fetch_naturalearth_places(limit: int = 700) -> List[Place]:
    resp = requests.get(NE_GEOJSON_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    feats = data.get("features") or []
    parsed: List[Tuple[float, Dict[str, Any]]] = []
    for f in feats:
        props = f.get("properties") or {}
        geom = f.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not coords or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        try:
            lonf = float(lon)
            latf = float(lat)
        except Exception:
            continue
        # Basic VIIRS coverage clamp; we’ll still keep out-of-range cities but
        # preloader will skip them later.
        latf = _clamp(latf, -90, 90)
        lonf = _clamp(lonf, -180, 180)

        name = props.get("name") or props.get("NAME")
        country = props.get("adm0name") or props.get("ADM0NAME") or props.get("sov0name")
        admin1 = props.get("adm1name") or props.get("ADM1NAME")
        if not name or not country:
            continue

        pop = props.get("pop_max") or props.get("POP_MAX") or 0
        try:
            popf = float(pop)
        except Exception:
            popf = 0.0
        parsed.append(
            (
                popf,
                {
                    "name": str(name),
                    "country": str(country),
                    "admin1": str(admin1) if admin1 else None,
                    "lat": latf,
                    "lon": lonf,
                },
            )
        )

    parsed.sort(key=lambda t: t[0], reverse=True)
    top = parsed[: limit]
    out: List[Place] = []
    for _, p in top:
        out.append(
            Place(
                name=p["name"],
                country=p["country"],
                admin1=p.get("admin1"),
                lat=float(p["lat"]),
                lon=float(p["lon"]),
                radius_km=None,
                place_type="city",
                tags=["natural_earth"],
                source="natural_earth",
            )
        )
    return out


def merge_places(*lists: Iterable[Place], target_size: int = 800) -> List[Place]:
    merged: List[Place] = []
    seen: Set[Tuple[str, str]] = set()

    # First pass: add everything that already has real coords
    pending_seeds: List[Place] = []
    for lst in lists:
        for p in lst:
            if p.lat == 0.0 and p.lon == 0.0 and p.source == "manual_seed":
                pending_seeds.append(p)
                continue
            k = p.key()
            if k in seen:
                continue
            seen.add(k)
            merged.append(p)

    # Build lookup from existing merged list by lowercase name+country for filling seed coords
    coord_lookup: Dict[Tuple[str, str], Place] = {p.key(): p for p in merged}

    # Second pass: fill seed coords from natural earth/project if possible
    for seed in pending_seeds:
        match = coord_lookup.get(seed.key())
        if match:
            merged.append(
                Place(
                    name=seed.name,
                    country=seed.country,
                    lat=match.lat,
                    lon=match.lon,
                    admin1=match.admin1,
                    place_type=seed.place_type,
                    radius_km=seed.radius_km or match.radius_km,
                    tags=sorted(set((seed.tags or []) + (match.tags or []))),
                    aliases=seed.aliases,
                    source="manual_seed_filled",
                )
            )
            continue
        # If still missing, skip (it will be handled by OSM in the preloader if desired)

    # Deduplicate again after fill
    final: List[Place] = []
    seen2: Set[Tuple[str, str]] = set()
    for p in merged:
        k = p.key()
        if k in seen2:
            continue
        # Filter out placeholder coords
        if p.lat == 0.0 and p.lon == 0.0:
            continue
        seen2.add(k)
        final.append(p)

    # Cap to target_size while keeping project list first
    if len(final) > target_size:
        final = final[:target_size]
    return final


def main() -> int:
    target_size = int(os.getenv("HOTLIST_SIZE", "800"))
    ne_limit = int(os.getenv("NE_LIMIT", "700"))

    project = load_project_cities()
    manual = manual_additions()
    # Pull more than target_size from Natural Earth so we can dedupe
    # and still land near HOTLIST_SIZE after merges.
    ne = fetch_naturalearth_places(limit=max(ne_limit, target_size * 2))
    places = merge_places(project, ne, manual, target_size=target_size)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_from": {
            "project_cities_data": True,
            "natural_earth_url": NE_GEOJSON_URL,
            "manual_seeds": True,
        },
        "count": len(places),
        "places": [asdict(p) for p in places],
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(places)} places to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

