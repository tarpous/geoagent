"""CRS helpers and demo AOI bounds."""

from __future__ import annotations

from dataclasses import dataclass

STORAGE_CRS = "EPSG:4326"
DEFAULT_METRIC_CRS = "EPSG:2100"


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
