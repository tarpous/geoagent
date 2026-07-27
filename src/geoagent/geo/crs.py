"""CRS helpers, demo AOI bounds, and offline metric approximations."""

from __future__ import annotations

import math
from dataclasses import dataclass

STORAGE_CRS = "EPSG:4326"
DEFAULT_METRIC_CRS = "EPSG:2100"

# Approximate meters per degree near Attica (~38°N) for offline buffers.
_M_PER_DEG_LAT = 111_320.0


@dataclass(frozen=True, slots=True)
class BBox:
    """Axis-aligned lon/lat bounding box in WGS84."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def intersects(self, other: BBox) -> bool:
        return not (
            self.max_lon < other.min_lon
            or self.min_lon > other.max_lon
            or self.max_lat < other.min_lat
            or self.min_lat > other.max_lat
        )

    def contains_point(self, lon: float, lat: float) -> bool:
        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat


# Approximate demo AOIs (WGS84). Tightened later when OSM clips land.
DEMO_AOIS: dict[str, BBox] = {
    "Attica": BBox(min_lon=23.0, min_lat=37.6, max_lon=24.2, max_lat=38.4),
    "Thessaloniki": BBox(min_lon=22.7, min_lat=40.4, max_lon=23.2, max_lat=40.8),
}


def union_demo_aoi() -> BBox:
    boxes = list(DEMO_AOIS.values())
    return BBox(
        min_lon=min(b.min_lon for b in boxes),
        min_lat=min(b.min_lat for b in boxes),
        max_lon=max(b.max_lon for b in boxes),
        max_lat=max(b.max_lat for b in boxes),
    )


def meters_per_deg_lon(lat: float) -> float:
    return _M_PER_DEG_LAT * math.cos(math.radians(lat))


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters (WGS84 sphere approximation)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def buffer_point_geojson(lon: float, lat: float, distance_m: float, *, steps: int = 32) -> dict:
    """Approximate geodesic buffer as a WGS84 polygon (CPU offline path)."""
    dlat = distance_m / _M_PER_DEG_LAT
    dlon = distance_m / max(1e-6, meters_per_deg_lon(lat))
    ring: list[list[float]] = []
    for i in range(steps + 1):
        ang = 2 * math.pi * i / steps
        ring.append([lon + dlon * math.cos(ang), lat + dlat * math.sin(ang)])
    return {"type": "Polygon", "coordinates": [ring]}


def bbox_geojson(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }
