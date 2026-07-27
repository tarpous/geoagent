"""Rate-limited, cached geocoding via Nominatim."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from geoagent.geo.validate import GeometryValidationError, validate_geojson

DEFAULT_CACHE = Path(".cache/geocode.json")
DEFAULT_USER_AGENT = "geoagent/0.1 (local-first geospatial analyst; contact: repo issues)"
MIN_INTERVAL_S = 1.1


@dataclass(slots=True)
class GeocodeResult:
    query: str
    display_name: str
    lon: float
    lat: float
    geojson: dict[str, Any]


class GeocodeCache:
    def __init__(self, path: Path = DEFAULT_CACHE) -> None:
        self.path = path
        self._data: dict[str, dict[str, Any]] = {}
        if path.is_file():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def get(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key.lower())

    def set(self, key: str, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data[key.lower()] = value
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


_last_call = 0.0


def geocode(
    query: str,
    *,
    cache: GeocodeCache | None = None,
    client: httpx.Client | None = None,
    require_demo_aoi: bool = True,
) -> GeocodeResult:
    """Geocode a place name. Uses Nominatim with a local disk cache and rate limit."""
    global _last_call
    cache = cache or GeocodeCache()
    cached = cache.get(query)
    if cached:
        point = {
            "type": "Point",
            "coordinates": [cached["lon"], cached["lat"]],
        }
        validate_geojson(point, require_demo_aoi=require_demo_aoi)
        return GeocodeResult(
            query=query,
            display_name=cached["display_name"],
            lon=float(cached["lon"]),
            lat=float(cached["lat"]),
            geojson=point,
        )

    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        wait = MIN_INTERVAL_S - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        response = client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        _last_call = time.monotonic()
        response.raise_for_status()
        rows = response.json()
        if not rows:
            raise LookupError(f"no geocode results for {query!r}")
        row = rows[0]
        lon = float(row["lon"])
        lat = float(row["lat"])
        point = {"type": "Point", "coordinates": [lon, lat]}
        try:
            validate_geojson(point, require_demo_aoi=require_demo_aoi)
        except GeometryValidationError:
            raise
        payload = {
            "display_name": row.get("display_name", query),
            "lon": lon,
            "lat": lat,
        }
        cache.set(query, payload)
        return GeocodeResult(
            query=query,
            display_name=payload["display_name"],
            lon=lon,
            lat=lat,
            geojson=point,
        )
    finally:
        if owns_client:
            client.close()
