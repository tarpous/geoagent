"""Rate-limited, cached geocoding via Nominatim with offline fixture fallback."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from geoagent.geo.validate import GeometryValidationError, validate_geojson

DEFAULT_CACHE = Path(".cache/geocode.json")
FIXTURE_CACHE = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "geocode_cache.json"
DEFAULT_USER_AGENT = "geoagent/0.1 (local-first geospatial analyst; contact: repo issues)"
MIN_INTERVAL_S = 1.1

# Deterministic demo AOI points used when network/Nominatim is unavailable.
OFFLINE_PLACES: dict[str, dict[str, Any]] = {
    "athens attica greece": {
        "display_name": "Athens, Attica, Greece",
        "lon": 23.7275,
        "lat": 37.9838,
    },
    "thessaloniki greece": {
        "display_name": "Thessaloniki, Greece",
        "lon": 22.9444,
        "lat": 40.6401,
    },
    "port of thessaloniki": {
        "display_name": "Port of Thessaloniki",
        "lon": 22.935,
        "lat": 40.635,
    },
}


@dataclass(slots=True)
class GeocodeResult:
    query: str
    display_name: str
    lon: float
    lat: float
    geojson: dict[str, Any]
    backend: str = "nominatim"


class GeocodeCache:
    def __init__(self, path: Path = DEFAULT_CACHE) -> None:
        self.path = path
        self._data: dict[str, dict[str, Any]] = {}
        if path.is_file():
            self._data = json.loads(path.read_text(encoding="utf-8"))
        elif FIXTURE_CACHE.is_file() and path == DEFAULT_CACHE:
            # Seed from committed fixture cache for offline CI.
            self._data = json.loads(FIXTURE_CACHE.read_text(encoding="utf-8"))

    def get(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key.lower())

    def set(self, key: str, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data[key.lower()] = value
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


_last_call = 0.0


def _from_payload(query: str, payload: dict[str, Any], *, backend: str) -> GeocodeResult:
    point = {"type": "Point", "coordinates": [payload["lon"], payload["lat"]]}
    return GeocodeResult(
        query=query,
        display_name=str(payload.get("display_name", query)),
        lon=float(payload["lon"]),
        lat=float(payload["lat"]),
        geojson=point,
        backend=backend,
    )


def _offline_lookup(query: str) -> dict[str, Any] | None:
    key = query.lower().strip()
    if key in OFFLINE_PLACES:
        return OFFLINE_PLACES[key]
    for place_key, payload in OFFLINE_PLACES.items():
        if place_key in key or key in place_key:
            return payload
    if "thessaloniki" in key or "salonika" in key:
        return OFFLINE_PLACES["thessaloniki greece"]
    if "attica" in key or "athens" in key:
        return OFFLINE_PLACES["athens attica greece"]
    return None


def geocode(
    query: str,
    *,
    cache: GeocodeCache | None = None,
    client: httpx.Client | None = None,
    require_demo_aoi: bool = True,
    allow_network: bool = True,
) -> GeocodeResult:
    """Geocode a place name. Prefers cache, then Nominatim, then offline fixtures."""
    global _last_call
    cache = cache or GeocodeCache()
    cached = cache.get(query)
    if cached:
        point = {
            "type": "Point",
            "coordinates": [cached["lon"], cached["lat"]],
        }
        validate_geojson(point, require_demo_aoi=require_demo_aoi)
        return _from_payload(query, cached, backend=str(cached.get("backend", "cache")))

    if allow_network:
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
            if rows:
                row = rows[0]
                lon = float(row["lon"])
                lat = float(row["lat"])
                point = {"type": "Point", "coordinates": [lon, lat]}
                validate_geojson(point, require_demo_aoi=require_demo_aoi)
                payload = {
                    "display_name": row.get("display_name", query),
                    "lon": lon,
                    "lat": lat,
                    "backend": "nominatim",
                }
                cache.set(query, payload)
                return _from_payload(query, payload, backend="nominatim")
        except (httpx.HTTPError, LookupError, GeometryValidationError, ValueError, KeyError):
            pass
        finally:
            if owns_client:
                client.close()

    offline = _offline_lookup(query)
    if offline is None:
        raise LookupError(f"no geocode results for {query!r}")
    point = {"type": "Point", "coordinates": [offline["lon"], offline["lat"]]}
    validate_geojson(point, require_demo_aoi=require_demo_aoi)
    payload = {**offline, "backend": "fixture"}
    cache.set(query, payload)
    return _from_payload(query, payload, backend="fixture")
