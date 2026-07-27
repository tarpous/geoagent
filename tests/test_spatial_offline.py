"""Offline spatial, OSM fixtures, imagery contracts."""

from __future__ import annotations

from geoagent.geo.crs import buffer_point_geojson, haversine_m
from geoagent.tools.spatial_sql import TEMPLATES, spatial_sql
from geoagent.tools.stac_imagery import ndvi_composite_stats


def test_spatial_sql_offline_buffer():
    result = spatial_sql(
        "buffer_point_m",
        {"lon": 23.72, "lat": 37.98, "distance_m": 2000},
        prefer_offline=True,
    )
    assert result["ok"] is True
    assert result["backend"] == "offline"
    assert result["geojson"]["type"] == "Polygon"
    # ~2 km buffer should span roughly that radius in lon/lat.
    ring = result["geojson"]["coordinates"][0]
    assert len(ring) >= 8


def test_roads_near_point_fixture():
    assert "roads_near_point" in TEMPLATES
    result = spatial_sql(
        "roads_near_point",
        {"lon": 23.72, "lat": 37.98, "distance_m": 2000},
    )
    assert result["ok"] is True
    assert result["count"] >= 1
    assert "OpenStreetMap" in result["attribution"]


def test_buffer_approx_radius():
    poly = buffer_point_geojson(23.72, 37.98, 2000)
    # Sample a vertex roughly east of center and check distance ~2 km.
    lon, lat = poly["coordinates"][0][0]
    dist = haversine_m(23.72, 37.98, lon, lat)
    assert 1500 < dist < 2500


def test_ndvi_declares_timezone_and_cloud_mask():
    stats = ndvi_composite_stats(
        bbox=[23.70, 37.90, 23.80, 38.00],
        start_date="2023-01-01",
        end_date="2024-12-31",
    )
    assert stats["timezone"] == "UTC"
    assert stats["inclusive"] is True
    assert "cloud_mask" in stats
