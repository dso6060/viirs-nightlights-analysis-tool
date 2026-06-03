"""
Load frozen study-area registries (Gulf ports, GDELT strike sites).

Coordinates and radii come only from JSON files — never invented at runtime.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]

GULF_PATH = os.getenv("VIIRS_GULF_STUDY_PATH", "backend/data/gulf_study_areas.json")
STRIKE_PATH = os.getenv("VIIRS_STRIKE_SITES_PATH", "backend/data/conflict_strike_sites.json")

_gulf_cache: Optional[Dict[str, Any]] = None
_strike_cache: Optional[Dict[str, Any]] = None
_lookup_cache: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None


def _resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    return p


def _norm(s: str) -> str:
    return (s or "").strip().casefold()


def _load_json(path_str: str) -> Dict[str, Any]:
    p = _resolve_path(path_str)
    if not p.is_file():
        return {"version": 1, "sites": []}
    return json.loads(p.read_text(encoding="utf-8"))


def load_gulf_study_areas() -> Dict[str, Any]:
    global _gulf_cache
    if _gulf_cache is None:
        _gulf_cache = _load_json(GULF_PATH)
    return _gulf_cache


def load_strike_sites() -> Dict[str, Any]:
    global _strike_cache
    if _strike_cache is None:
        _strike_cache = _load_json(STRIKE_PATH)
    return _strike_cache


def _rebuild_lookup() -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for payload, source_kind in (
        (load_gulf_study_areas(), "gulf_port"),
        (load_strike_sites(), "gdelt_strike"),
    ):
        for site in payload.get("sites") or []:
            label = str(site.get("label") or "").strip()
            country = str(site.get("country") or "").strip()
            if not label or not country:
                continue
            key = (_norm(label), _norm(country))
            entry = dict(site)
            entry["source_kind"] = source_kind
            entry["registry_disclaimer"] = payload.get("disclaimer") or ""
            entry["registry_radius_methodology"] = payload.get("radius_methodology") or ""
            entry["human_curated"] = bool(payload.get("human_curated"))
            out[key] = entry
    return out


def _lookup() -> Dict[Tuple[str, str], Dict[str, Any]]:
    global _lookup_cache
    if _lookup_cache is None:
        _lookup_cache = _rebuild_lookup()
    return _lookup_cache


def invalidate_cache() -> None:
    global _gulf_cache, _strike_cache, _lookup_cache
    _gulf_cache = None
    _strike_cache = None
    _lookup_cache = None


def resolve_study_area(city: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Match by exact label + country (case-insensitive)."""
    if not city or not country:
        return None
    return _lookup().get((_norm(city), _norm(country)))


def study_area_to_city_info(site: Dict[str, Any], query_city: str) -> Dict[str, Any]:
    return {
        "city": query_city,
        "country": site["country"],
        "lat": float(site["lat"]),
        "lon": float(site["lon"]),
        "radius_km": float(site["radius_km"]),
        "display_name": f"{site.get('label', query_city)}, {site['country']}",
        "osm_id": site.get("id") or "",
        "place_type": site.get("source_kind") or "study_area",
        "study_area_id": site.get("id"),
        "radius_rationale": site.get("radius_rationale") or site.get("registry_radius_methodology") or "",
        "human_curated": site.get("human_curated"),
        "event_date": site.get("event_date"),
        "geo_precision": site.get("geo_precision"),
    }


def sites_for_cluster_places(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return study-area detail rows for cluster members (for UI radius panel)."""
    rows: List[Dict[str, Any]] = []
    for p in places or []:
        city = p.get("city")
        country = p.get("country")
        site = resolve_study_area(str(city or ""), str(country or "") if country else None)
        if site:
            rows.append(
                {
                    "label": site.get("label") or city,
                    "country": site.get("country") or country,
                    "lat": site.get("lat"),
                    "lon": site.get("lon"),
                    "radius_km": site.get("radius_km"),
                    "radius_rationale": site.get("radius_rationale")
                    or site.get("registry_radius_methodology"),
                    "human_curated": site.get("human_curated"),
                    "event_date": site.get("event_date"),
                    "geo_precision": site.get("geo_precision"),
                    "source_kind": site.get("source_kind"),
                }
            )
        else:
            rows.append(
                {
                    "label": city,
                    "country": country,
                    "radius_km": p.get("radius_km"),
                    "radius_rationale": p.get("radius_rationale"),
                }
            )
    return rows
