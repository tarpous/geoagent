"""Allowlisted spatial SQL templates (PostGIS when available, offline fallback)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from geoagent.geo.crs import (
    DEFAULT_METRIC_CRS,
    STORAGE_CRS,
    bbox_geojson,
    buffer_point_geojson,
    haversine_m,
)

TemplateName = Literal[
    "buffer_point_m",
    "aoi_bbox",
    "distance_m",
    "roads_near_point",
    "landuse_in_aoi",
]

ROOT = Path(__file__).resolve().parents[3]
OSM_FIXTURES = ROOT / "data" / "fixtures" / "osm"

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
    # OSM templates are fixture-backed offline; PostGIS variants can replace later.
    "roads_near_point": "",
    "landuse_in_aoi": "",
}


def _offline(template: TemplateName, params: dict[str, Any]) -> dict[str, Any]:
    if template == "buffer_point_m":
        geojson = buffer_point_geojson(
            float(params["lon"]),
            float(params["lat"]),
            float(params["distance_m"]),
        )
        return {
            "ok": True,
            "template": template,
            "geojson": geojson,
            "crs": STORAGE_CRS,
            "backend": "offline",
            "metric_crs": DEFAULT_METRIC_CRS,
        }
    if template == "aoi_bbox":
        geojson = bbox_geojson(
            float(params["min_lon"]),
            float(params["min_lat"]),
            float(params["max_lon"]),
            float(params["max_lat"]),
        )
        return {
            "ok": True,
            "template": template,
            "geojson": geojson,
            "crs": STORAGE_CRS,
            "backend": "offline",
        }
    if template == "distance_m":
        dist = haversine_m(
            float(params["lon1"]),
            float(params["lat1"]),
            float(params["lon2"]),
            float(params["lat2"]),
        )
        return {
            "ok": True,
            "template": template,
            "distance_m": dist,
            "unit": "m",
            "backend": "offline",
        }
    if template == "roads_near_point":
        return _roads_near_point_offline(params)
    if template == "landuse_in_aoi":
        return _landuse_in_aoi_offline(params)
    raise ValueError(f"unknown spatial template: {template}")


def _load_osm(name: str) -> dict[str, Any]:
    path = OSM_FIXTURES / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _point_near_line(lon: float, lat: float, coords: list[list[float]], max_m: float) -> bool:
    return any(haversine_m(lon, lat, c[0], c[1]) <= max_m for c in coords)


def _roads_near_point_offline(params: dict[str, Any]) -> dict[str, Any]:
    lon, lat = float(params["lon"]), float(params["lat"])
    distance_m = float(params.get("distance_m", 2000))
    data = _load_osm("attica_ring_road.geojson")
    hits = []
    for feat in data.get("features") or []:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if geom.get("type") == "LineString" and _point_near_line(lon, lat, coords, distance_m):
            hits.append(feat)
    return {
        "ok": True,
        "template": "roads_near_point",
        "features": hits,
        "count": len(hits),
        "geojson": {"type": "FeatureCollection", "features": hits},
        "crs": STORAGE_CRS,
        "backend": "osm-fixture",
        "attribution": "© OpenStreetMap contributors (ODbL)",
    }


def _landuse_in_aoi_offline(params: dict[str, Any]) -> dict[str, Any]:
    aoi = str(params.get("aoi", "Attica"))
    data = _load_osm("landuse_samples.geojson")
    hits = [
        f
        for f in data.get("features") or []
        if (f.get("properties") or {}).get("aoi") == aoi
    ]
    return {
        "ok": True,
        "template": "landuse_in_aoi",
        "features": hits,
        "count": len(hits),
        "geojson": {"type": "FeatureCollection", "features": hits},
        "crs": STORAGE_CRS,
        "backend": "osm-fixture",
        "attribution": "© OpenStreetMap contributors (ODbL)",
    }


def spatial_sql(
    template: TemplateName,
    params: dict[str, Any],
    *,
    dsn: str | None = None,
    prefer_offline: bool = False,
) -> dict[str, Any]:
    """Run an allowlisted spatial template (PostGIS) or offline/OSM fixture fallback."""
    if template not in TEMPLATES:
        raise ValueError(f"unknown spatial template: {template}")

    # OSM templates are fixture-only until PostGIS OSM tables exist.
    if template in {"roads_near_point", "landuse_in_aoi"} or prefer_offline:
        return _offline(template, params)

    try:
        from geoagent.db import connect

        sql = TEMPLATES[template]
        if not sql.strip():
            return _offline(template, params)
        bound = {
            "metric_srid": int(DEFAULT_METRIC_CRS.split(":")[1]),
            "storage_crs": STORAGE_CRS,
            **params,
        }
        with connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, bound)
            row = cur.fetchone()
            if row is None:
                return {"ok": False, "error": "empty_result", "backend": "postgis"}
            if template == "distance_m":
                return {
                    "ok": True,
                    "template": template,
                    "distance_m": float(row[0]),
                    "unit": "m",
                    "backend": "postgis",
                }
            geojson = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            return {
                "ok": True,
                "template": template,
                "geojson": geojson,
                "crs": STORAGE_CRS,
                "backend": "postgis",
            }
    except Exception as exc:  # noqa: BLE001
        result = _offline(template, params)
        result["warning"] = f"postgis_unavailable:{type(exc).__name__}"
        return result
