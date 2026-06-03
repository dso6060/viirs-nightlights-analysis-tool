"""
English/Latin place-name helpers for UI, cache keys, and OSM normalization.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Common localized country labels → English (fallback if accept-language is ignored).
_COUNTRY_EN: Dict[str, str] = {
    "السعودية": "Saudi Arabia",
    "المملكة العربية السعودية": "Saudi Arabia",
    "ایران": "Iran",
    "إيران": "Iran",
    "الإمارات العربية المتحدة": "United Arab Emirates",
    "الإمارات": "United Arab Emirates",
    "سلطنة عمان": "Oman",
    "عُمان": "Oman",
    "العراق": "Iraq",
    "قطر": "Qatar",
    "الكويت": "Kuwait",
    "البحرين": "Bahrain",
    "اليمن": "Yemen",
    "سوريا": "Syria",
    "لبنان": "Lebanon",
    "الأردن": "Jordan",
    "مصر": "Egypt",
    "فلسطين": "Palestine",
    "State of Palestine": "Palestine",
    "Palestinian Territory": "Palestine",
    "ישראל": "Israel",
    "Україна": "Ukraine",
    "Россия": "Russia",
    "Российская Федерация": "Russia",
    "中国": "China",
    "日本": "Japan",
    "대한민국": "South Korea",
    "Република Казахстан": "Kazakhstan",
}

_LATIN_RE = re.compile(r"^[\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\s\-\.'(),]+$")


def is_latin_text(text: Optional[str]) -> bool:
    if not text or not str(text).strip():
        return False
    return bool(_LATIN_RE.match(str(text).strip()))


def english_country(country: Optional[str]) -> str:
    c = (country or "").strip()
    if not c:
        return c
    if is_latin_text(c):
        return c
    return _COUNTRY_EN.get(c, c)


def pick_english_name(
    user_query: Optional[str],
    osm_name: Optional[str],
    namedetails: Optional[Dict[str, Any]] = None,
) -> str:
    """Prefer user Latin query, then OSM name:en, then Latin OSM name."""
    if user_query and is_latin_text(user_query):
        return user_query.strip()
    if namedetails:
        for key in ("name:en", "name:en-gb", "name:en-us", "name:international"):
            val = namedetails.get(key)
            if val and is_latin_text(val):
                return str(val).strip()
    if osm_name and is_latin_text(osm_name):
        return str(osm_name).strip()
    if user_query:
        return user_query.strip()
    return (osm_name or user_query or "").strip()


def build_display_name(city: str, country: str, admin1: Optional[str] = None) -> str:
    city = (city or "").strip()
    country = english_country(country)
    if admin1 and is_latin_text(admin1):
        return f"{city}, {admin1}, {country}"
    return f"{city}, {country}" if country else city
