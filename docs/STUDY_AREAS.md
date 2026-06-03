# Study areas (user-request + GDELT)

## Gulf ports (Section 1 — user-request)

- Data: `backend/data/gulf_study_areas.json`
- 16 Hormuz/Gulf ports with **frozen lat/lon** and **manual radius_km (3–6 km)**
- Clusters: `ports-gulf-hormuz-a`, `ports-gulf-hormuz-b` in `backend/data/clusters.json`
- UI shows per-port radius rationale when a cluster is selected

## GDELT strikes (Sections 2 & 3)

- Build script: `scripts/build_conflict_strike_sites.py` (requires `GDELT_CLOUD_API_KEY`)
- Output: `backend/data/conflict_strike_sites.json` + updates `missile-hit-here` / `drone-strike-sites` in clusters.json
- **No fabricated coordinates** — if the API key is missing, sites stay empty and GDELT buttons are disabled

## Preload cache

```bash
export VIIRS_SOURCE=gee  # or noaa for local smoke
export VIIRS_DB_PATH=backend/viirs_cache_local.db
python3 scripts/preload_study_areas.py --start 2021-01 --end latest
```

## Radius methodology (summary)

| Source | How radius_km is set |
|--------|----------------------|
| Gulf ports | Manual per terminal in JSON (~750 m VIIRS pixels; square ±radius box) |
| GDELT strikes | Auto: geo_precision 1→2.0 km, 2→2.5 km (precision 3 excluded) |
