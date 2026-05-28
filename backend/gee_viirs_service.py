"""
Google Earth Engine VIIRS monthly service.

Uses the Earth Engine ImageCollection:
  NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG

This avoids scraping NOAA file listings and works well for preloading a small
set of cities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from bias_correction import BiasCorrection


@dataclass(frozen=True)
class GEEServiceConfig:
    project_id: str
    collection_id: str = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG"
    radiance_band: str = "avg_rad"
    cf_cvg_band: str = "cf_cvg"


class GEEVIIRSService:
    def __init__(self, config: GEEServiceConfig):
        self.config = config
        self._ee = None

    def _ensure_init(self):
        if self._ee is not None:
            return

        import ee  # type: ignore

        # Prefer explicit service-account credentials to avoid any interactive auth flow.
        # GOOGLE_APPLICATION_CREDENTIALS should point to the service-account JSON.
        import os
        import json

        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not sa_path:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS must be set to a service-account JSON path for GEE mode"
            )

        with open(sa_path, "r", encoding="utf-8") as f:
            sa = json.load(f)

        sa_email = sa.get("client_email")
        if not sa_email:
            raise RuntimeError("Service account JSON missing client_email")

        creds = ee.ServiceAccountCredentials(sa_email, sa_path)
        ee.Initialize(credentials=creds, project=self.config.project_id)
        self._ee = ee

    @staticmethod
    def _parse_ym(s: str) -> datetime:
        return datetime.strptime(s, "%Y-%m")

    @staticmethod
    def _generate_date_range(start: str, end: str) -> List[str]:
        start_dt = datetime.strptime(start, "%Y-%m")
        end_dt = datetime.strptime(end, "%Y-%m")
        out: List[str] = []
        cur = start_dt
        while cur <= end_dt:
            out.append(cur.strftime("%Y-%m"))
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return out

    def fetch_viirs_for_city(
        self,
        city_name: str,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        start_date: str = "2019-01",
        end_date: str = "2024-12",
    ) -> List[Dict]:
        self._ensure_init()
        ee = self._ee
        assert ee is not None

        dates = self._generate_date_range(start_date, end_date)
        results: List[Dict] = []

        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(radius_km * 1000).bounds()

        for ym in dates:
            start = self._parse_ym(ym)
            # Filter month [start, next_month)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)

            img = (
                ee.ImageCollection(self.config.collection_id)
                .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                .first()
            )

            # Some months may be missing for config; skip if no image
            info = img.getInfo()
            if info is None:
                continue

            # Mean within region
            reducer = ee.Reducer.mean()
            stats = (
                img.select([self.config.radiance_band, self.config.cf_cvg_band])
                .reduceRegion(reducer=reducer, geometry=region, scale=500, maxPixels=1e9)
                .getInfo()
            )

            if not stats:
                continue

            rad = stats.get(self.config.radiance_band)
            cf = stats.get(self.config.cf_cvg_band)

            if rad is None:
                continue

            # GEE cf_cvg is count of cloud-free observations; convert to a pseudo-percentage
            # only if it looks like a percentage (some products store 0..100). If not, pass None.
            cf_pct: Optional[float]
            if isinstance(cf, (int, float)) and 0 <= float(cf) <= 100:
                cf_pct = float(cf)
            else:
                cf_pct = None

            # Treat months with very low cloud-free observations as "missing/low quality".
            # cf_cvg is typically a count (0..~80), not a percentage.
            min_cf = float(__import__("os").getenv("MIN_CF_CVG", "5"))
            is_low_quality = isinstance(cf, (int, float)) and float(cf) < min_cf
            corrected = None if is_low_quality else BiasCorrection.apply_correction(float(rad), cf_pct)

            results.append(
                {
                    "date": ym,
                    "city": city_name,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "radiance": None if is_low_quality else float(rad),
                    "radiance_corrected": None if corrected is None else float(corrected),
                    "cloud_free_coverage": float(cf) if isinstance(cf, (int, float)) else None,
                    "data_quality": "low" if is_low_quality else "ok",
                }
            )

        return results

    def get_latest_available_month(self) -> Dict[str, int]:
        """
        Return latest available month for the chosen ImageCollection.

        This is used by the frontend badge. It returns the latest month present in the collection.
        """
        self._ensure_init()
        ee = self._ee
        assert ee is not None

        col = ee.ImageCollection(self.config.collection_id).sort("system:time_start", False)
        img = col.first()
        ts = img.get("system:time_start").getInfo()
        # system:time_start is milliseconds since epoch
        dt = datetime.utcfromtimestamp(ts / 1000.0)
        return {"year": dt.year, "month": dt.month}

