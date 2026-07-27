"""CRS, units, and geometry validator tests."""

from __future__ import annotations

import pytest

from geoagent.geo import (
    DEFAULT_METRIC_CRS,
    STORAGE_CRS,
    GeometryValidationError,
    convert_area,
    convert_length,
    validate_geojson,
)


def test_crs_defaults():
    assert STORAGE_CRS == "EPSG:4326"
    assert DEFAULT_METRIC_CRS == "EPSG:2100"


def test_unit_conversions():
    assert convert_length(2.0, "km", "m") == 2000.0
    assert convert_area(1.0, "ha", "m2") == 10_000.0


def test_validate_attica_polygon():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [23.7, 37.9],
                [23.8, 37.9],
                [23.8, 38.0],
                [23.7, 38.0],
                [23.7, 37.9],
            ]
        ],
    }
    bbox = validate_geojson(geojson)
    assert bbox.min_lon == 23.7


def test_reject_empty_nan_and_out_of_aoi():
    with pytest.raises(GeometryValidationError):
        validate_geojson({"type": "Point", "coordinates": []})
    with pytest.raises(GeometryValidationError):
        validate_geojson({"type": "Point", "coordinates": [float("nan"), 38.0]})
    with pytest.raises(GeometryValidationError):
        validate_geojson({"type": "Point", "coordinates": [0.0, 0.0]})
    # Opt-out path for non-demo AOIs.
    bbox = validate_geojson(
        {"type": "Point", "coordinates": [0.0, 0.0]},
        require_demo_aoi=False,
    )
    assert bbox.min_lon == 0.0
