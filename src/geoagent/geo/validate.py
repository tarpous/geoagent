"""Geometry sanity validators used by tools and the critic."""

from __future__ import annotations

import math
from typing import Any

from geoagent.geo.crs import DEMO_AOIS, BBox, union_demo_aoi


class GeometryValidationError(ValueError):
    """Raised when a geometry fails geoagent sanity checks."""


def _iter_coords(obj: Any) -> list[tuple[float, float]]:
    if obj is None:
        return []
    if isinstance(obj, (list, tuple)):
        if len(obj) >= 2 and all(isinstance(v, (int, float)) for v in obj[:2]):
            return [(float(obj[0]), float(obj[1]))]
        coords: list[tuple[float, float]] = []
        for item in obj:
            coords.extend(_iter_coords(item))
        return coords
    return []


def _bbox_from_coords(coords: list[tuple[float, float]]) -> BBox:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return BBox(min_lon=min(lons), min_lat=min(lats), max_lon=max(lons), max_lat=max(lats))


def validate_geojson(
    geojson: dict[str, Any],
    *,
    require_demo_aoi: bool = True,
    max_area_deg2: float = 4.0,
) -> BBox:
    """Validate a GeoJSON object for emptiness, finiteness, and demo AOI overlap."""
    if not isinstance(geojson, dict):
        raise GeometryValidationError("geojson must be an object")

    gtype = geojson.get("type")
    if not gtype:
        raise GeometryValidationError("geojson missing type")

    if gtype == "Feature":
        geometry = geojson.get("geometry")
        if not geometry:
            raise GeometryValidationError("Feature has empty geometry")
        return validate_geojson(
            geometry, require_demo_aoi=require_demo_aoi, max_area_deg2=max_area_deg2
        )
    if gtype == "FeatureCollection":
        features = geojson.get("features") or []
        if not features:
            raise GeometryValidationError("FeatureCollection is empty")
        boxes = [
            validate_geojson(f, require_demo_aoi=require_demo_aoi, max_area_deg2=max_area_deg2)
            for f in features
        ]
        return BBox(
            min_lon=min(b.min_lon for b in boxes),
            min_lat=min(b.min_lat for b in boxes),
            max_lon=max(b.max_lon for b in boxes),
            max_lat=max(b.max_lat for b in boxes),
        )

    coords = _iter_coords(geojson.get("coordinates"))
    if not coords:
        raise GeometryValidationError("geometry has no coordinates")

    for lon, lat in coords:
        if not math.isfinite(lon) or not math.isfinite(lat):
            raise GeometryValidationError("non-finite coordinate")
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise GeometryValidationError("coordinate out of WGS84 bounds")

    bbox = _bbox_from_coords(coords)
    area_deg2 = (bbox.max_lon - bbox.min_lon) * (bbox.max_lat - bbox.min_lat)
    if area_deg2 > max_area_deg2:
        raise GeometryValidationError(f"AOI too large: {area_deg2:.3f} deg^2")

    if require_demo_aoi:
        demo = union_demo_aoi()
        if not bbox.intersects(demo):
            known = ", ".join(DEMO_AOIS)
            raise GeometryValidationError(
                f"geometry outside demo AOIs ({known}); pass require_demo_aoi=False to opt out"
            )
    return bbox
