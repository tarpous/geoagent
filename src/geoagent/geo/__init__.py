"""Geospatial correctness helpers."""

from geoagent.geo.crs import (
    DEFAULT_METRIC_CRS,
    DEMO_AOIS,
    STORAGE_CRS,
    BBox,
    union_demo_aoi,
)
from geoagent.geo.units import ALLOWED_UNITS, assert_known_unit, convert_area, convert_length
from geoagent.geo.validate import GeometryValidationError, validate_geojson

__all__ = [
    "ALLOWED_UNITS",
    "DEFAULT_METRIC_CRS",
    "DEMO_AOIS",
    "STORAGE_CRS",
    "BBox",
    "GeometryValidationError",
    "assert_known_unit",
    "convert_area",
    "convert_length",
    "union_demo_aoi",
    "validate_geojson",
]
