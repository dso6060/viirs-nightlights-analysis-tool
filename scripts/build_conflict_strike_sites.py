#!/usr/bin/env python3
"""
Build conflict_strike_sites.json from GDELT Cloud conflict events.

Requires GDELT_CLOUD_API_KEY in environment or backend/.env.
Does NOT invent coordinates — only writes events returned by the API.

Usage:
  export GDELT_CLOUD_API_KEY=gdelt_sk_...
  python3 scripts/build_conflict_strike_sites.py

Optional:
  --max-per-cluster 12
  --max-per-country 2
  --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
STRIKE_JSON = ROOT / "backend" / "data" / "conflict_strike_sites.json"
CLUSTERS_JSON = ROOT / "backend" / "data" / "clusters.json"

GDELT_BASE = "https://gdeltcloud.com/api/v2/events"

COUNTRIES = [
    "Ukraine",
    "Russia",
    "Israel",
    "Palestine",
    "Lebanon",
    "Yemen",
    "Iran",
    "Iraq",
    "United Arab Emirates",
    "Saudi Arabia",
    "Oman",
    "Pakistan",
    "India",
]

DATE_START = "2021-06-01"

MISSILE_SUBCATEGORY_RE = re.compile(
    r"shell|artillery|missile|rocket|mortar|bombard", re.I
)
DRONE_SUBCATEGORY_RE = re.compile(r"air.?/?.?drone|drone strike|airstrike|air strike", re.I)


def load_dotenv() -> None:
    env_path = ROOT / "backend" / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key() -> str:
    load_dotenv()
    key = os.getenv("GDELT_CLOUD_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: GDELT_CLOUD_API_KEY not set. Register at https://gdeltcloud.com — "
            "no strike sites will be fabricated.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def radius_for_precision(geo_precision: Optional[int]) -> Optional[float]:
    if geo_precision is None:
        return None
    if geo_precision >= 3:
        return None
    if geo_precision == 1:
        return 2.0
    if geo_precision == 2:
        return 2.5
    return 3.0


def fetch_events(
    session: requests.Session,
    *,
    country: str,
    search: str,
    date_start: str,
    date_end: str,
    max_pages: int = 20,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    for _ in range(max_pages):
        params: Dict[str, Any] = {
            "event_family": "conflict",
            "country": country,
            "search": search,
            "date_start": date_start,
            "date_end": date_end,
            "limit": 100,
            "sort": "significance",
        }
        if cursor:
            params["cursor"] = cursor
        resp = session.get(GDELT_BASE, params=params, timeout=90)
        if resp.status_code != 200:
            print(f"WARN: GDELT {country} search={search!r} HTTP {resp.status_code}", file=sys.stderr)
            break
        payload = resp.json()
        if not payload.get("success"):
            print(f"WARN: GDELT error for {country}: {payload}", file=sys.stderr)
            break
        batch = payload.get("data") or []
        out.extend(batch)
        pagination = payload.get("pagination") or {}
        cursor = pagination.get("next_cursor")
        if not cursor or not batch:
            break
    return out


def normalize_event(ev: Dict[str, Any], cluster: str) -> Optional[Dict[str, Any]]:
    geo = ev.get("geo") or {}
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    if lat is None or lon is None:
        return None
    geo_precision = geo.get("geo_precision")
    if geo_precision is None:
        geo_precision = ev.get("geo_precision")
    try:
        geo_precision = int(geo_precision) if geo_precision is not None else None
    except (TypeError, ValueError):
        geo_precision = None

    radius_km = radius_for_precision(geo_precision)
    if radius_km is None:
        return None

    country = geo.get("country") or geo.get("location_country") or ""
    location = geo.get("location") or geo.get("admin1") or country
    event_date = (ev.get("event_date") or "")[:10]
    subcategory = str(ev.get("subcategory") or "")
    fatalities = ev.get("fatalities")
    try:
        fatalities = int(fatalities) if fatalities is not None else 0
    except (TypeError, ValueError):
        fatalities = 0

    eid = str(ev.get("id") or ev.get("event_code") or "")
    label = f"{location} — GDELT {cluster.split('-')[0]} ({event_date})"

    return {
        "id": f"{cluster}-{eid}"[:80],
        "cluster": cluster,
        "label": label[:120],
        "country": country,
        "lat": float(lat),
        "lon": float(lon),
        "radius_km": radius_km,
        "radius_rationale": f"Auto: GDELT geo_precision={geo_precision} → {radius_km} km (VIIRS ~750 m pixels in ±{radius_km} km square box).",
        "event_date": event_date,
        "source_id": eid,
        "sub_event_type": subcategory,
        "geo_precision": geo_precision,
        "fatalities": fatalities,
    }


def dedupe_and_cap(
    rows: List[Dict[str, Any]],
    *,
    max_cluster: int,
    max_per_country: int,
) -> List[Dict[str, Any]]:
    # Sort by fatalities desc, then date desc
    rows.sort(key=lambda r: (r.get("fatalities") or 0, r.get("event_date") or ""), reverse=True)

    seen: Set[Tuple[str, float, float]] = set()
    country_counts: Dict[str, int] = defaultdict(int)
    out: List[Dict[str, Any]] = []

    for row in rows:
        if len(out) >= max_cluster:
            break
        c = (row.get("country") or "").casefold()
        lat_r = round(float(row["lat"]), 2)
        lon_r = round(float(row["lon"]), 2)
        dedupe_key = (c, lat_r, lon_r)
        if dedupe_key in seen:
            continue
        if max_per_country and country_counts[c] >= max_per_country:
            continue
        seen.add(dedupe_key)
        country_counts[c] += 1
        out.append(row)
    return out


def classify_and_collect(all_events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    missile_raw: List[Dict[str, Any]] = []
    drone_raw: List[Dict[str, Any]] = []
    for ev in all_events:
        sub = str(ev.get("subcategory") or "")
        title = str(ev.get("title") or "")
        blob = f"{sub} {title}"
        norm_m = normalize_event(ev, "missile-hit-here") if MISSILE_SUBCATEGORY_RE.search(blob) else None
        norm_d = normalize_event(ev, "drone-strike-sites") if DRONE_SUBCATEGORY_RE.search(blob) else None
        if norm_m:
            missile_raw.append(norm_m)
        if norm_d:
            drone_raw.append(norm_d)
    return missile_raw, drone_raw


def sync_clusters_json(sites: List[Dict[str, Any]]) -> None:
    clusters_data = json.loads(CLUSTERS_JSON.read_text(encoding="utf-8"))
    by_cluster: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for s in sites:
        by_cluster[s["cluster"]].append(s)

    for c in clusters_data.get("clusters") or []:
        cid = c.get("id")
        if cid == "missile-hit-here":
            picked = by_cluster.get("missile-hit-here") or []
            c["places"] = [{"city": p["label"], "country": p["country"]} for p in picked]
            c["countries_covered"] = sorted({p["country"] for p in picked if p.get("country")})
        elif cid == "drone-strike-sites":
            picked = by_cluster.get("drone-strike-sites") or []
            c["places"] = [{"city": p["label"], "country": p["country"]} for p in picked]
            c["countries_covered"] = sorted({p["country"] for p in picked if p.get("country")})

    CLUSTERS_JSON.write_text(json.dumps(clusters_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GDELT strike sites JSON (no fabricated data)")
    parser.add_argument("--max-per-cluster", type=int, default=12)
    parser.add_argument("--max-per-country", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date-end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args = parser.parse_args()

    key = api_key()
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}"})

    all_events: List[Dict[str, Any]] = []
    searches = ["missile strike", "artillery shelling", "drone strike", "air strike"]

    for country in COUNTRIES:
        for search in searches:
            batch = fetch_events(
                session,
                country=country,
                search=search,
                date_start=DATE_START,
                date_end=args.date_end,
            )
            all_events.extend(batch)
            print(f"  {country} / {search}: +{len(batch)} events")

    missile_raw, drone_raw = classify_and_collect(all_events)
    missile = dedupe_and_cap(
        missile_raw, max_cluster=args.max_per_cluster, max_per_country=args.max_per_country
    )
    drone = dedupe_and_cap(
        drone_raw, max_cluster=args.max_per_cluster, max_per_country=args.max_per_country
    )
    sites = missile + drone

    print(f"Missile cluster: {len(missile)} sites | Drone cluster: {len(drone)} sites")

    if args.dry_run:
        print("Dry run — not writing files.")
        return

    strike_doc = {
        "version": 1,
        "source": "GDELT Cloud conflict events",
        "human_curated": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": json.loads(STRIKE_JSON.read_text(encoding="utf-8")).get("disclaimer"),
        "radius_methodology": json.loads(STRIKE_JSON.read_text(encoding="utf-8")).get("radius_methodology"),
        "countries_filter": COUNTRIES,
        "sites": sites,
    }
    STRIKE_JSON.write_text(json.dumps(strike_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sync_clusters_json(sites)
    print(f"Wrote {STRIKE_JSON} and updated {CLUSTERS_JSON}")


if __name__ == "__main__":
    main()
