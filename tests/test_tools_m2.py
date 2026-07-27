"""Tool layer tests (Postgres-backed tests skip when DB is down)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geoagent.tools.mapping import make_map
from geoagent.tools.spatial_sql import spatial_sql


def _db_available() -> bool:
    try:
        import psycopg

        with psycopg.connect(
            "postgresql://geoagent:geoagent@127.0.0.1:5432/geoagent",
            connect_timeout=2,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT PostGIS_Version()")
                cur.fetchone()
        return True
    except Exception:
        return False


def test_make_map_writes_geojson(tmp_path: Path):
    artifacts = make_map(
        [{"name": "pt", "geojson": {"type": "Point", "coordinates": [23.7, 37.9]}}],
        out_dir=tmp_path,
        name="demo",
    )
    assert artifacts["geojson"].is_file()
    data = json.loads(artifacts["geojson"].read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1


@pytest.mark.skipif(not _db_available(), reason="PostGIS not available")
def test_spatial_buffer_and_distance():
    buffered = spatial_sql(
        "buffer_point_m",
        {"lon": 23.72, "lat": 37.98, "distance_m": 2000},
    )
    assert buffered["ok"] is True
    assert buffered["geojson"]["type"] == "Polygon"

    dist = spatial_sql(
        "distance_m",
        {"lon1": 23.72, "lat1": 37.98, "lon2": 23.73, "lat2": 37.99},
    )
    assert dist["ok"] is True
    assert dist["distance_m"] > 0
