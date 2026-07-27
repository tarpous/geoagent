"""Allowlisted PostGIS spatial SQL templates (no raw model SQL)."""

from __future__ import annotations

from typing import Any, Literal

from geoagent.db import connect
from geoagent.geo.crs import DEFAULT_METRIC_CRS, STORAGE_CRS

TemplateName = Literal["buffer_point_m", "aoi_bbox", "distance_m"]


TEMPLATES: dict[TemplateName, str] = {
    "buffer_point_m": """
        SELECT ST_AsGeoJSON(
            ST_Transform(
                ST_Buffer(
                    ST_Transform(
                        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326),
                        %(metric_srid)s
                    ),
                    %(distance_m)s
                ),
                4326
            )
        ) AS geojson
    """,
    "aoi_bbox": """
        SELECT ST_AsGeoJSON(
            ST_MakeEnvelope(%(min_lon)s, %(min_lat)s, %(max_lon)s, %(max_lat)s, 4326)
        ) AS geojson
    """,
    "distance_m": """
        SELECT ST_Distance(
            ST_Transform(ST_SetSRID(ST_MakePoint(%(lon1)s, %(lat1)s), 4326), %(metric_srid)s),
            ST_Transform(ST_SetSRID(ST_MakePoint(%(lon2)s, %(lat2)s), 4326), %(metric_srid)s)
        ) AS distance_m
    """,
}


def spatial_sql(
    template: TemplateName,
    params: dict[str, Any],
    *,
    dsn: str | None = None,
) -> dict[str, Any]:
    """Run an allowlisted spatial template against PostGIS."""
    if template not in TEMPLATES:
        raise ValueError(f"unknown spatial template: {template}")
    sql = TEMPLATES[template]
    bound = {
        "metric_srid": int(DEFAULT_METRIC_CRS.split(":")[1]),
        "storage_crs": STORAGE_CRS,
        **params,
    }
    with connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, bound)
        row = cur.fetchone()
        if row is None:
            return {"ok": False, "error": "empty_result"}
        if template == "distance_m":
            return {
                "ok": True,
                "template": template,
                "distance_m": float(row[0]),
                "unit": "m",
            }
        import json

        geojson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return {"ok": True, "template": template, "geojson": geojson, "crs": STORAGE_CRS}
