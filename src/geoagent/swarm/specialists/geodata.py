"""Geodata specialist."""

from __future__ import annotations

from geoagent.tools.geocode import geocode
from geoagent.tools.spatial_sql import spatial_sql
from geoagent.swarm.handoffs import handoff_to
from geoagent.swarm.state import TeamState

_AOI_POINTS = {
    "Attica": (23.72, 37.98, "Athens Attica Greece"),
    "Thessaloniki": (22.94, 40.64, "Thessaloniki Greece"),
}


def run_geodata(state: TeamState) -> TeamState:
    aoi = state.aoi or "Attica"
    lon, lat, place = _AOI_POINTS.get(aoi, _AOI_POINTS["Attica"])
    try:
        geo = geocode(place, require_demo_aoi=True)
        lon, lat = geo.lon, geo.lat
        state.evidence.append({"tool": "geocode", "display_name": geo.display_name})
        state.geometries.append({"name": "geocode", "geojson": geo.geojson})
        state.tool_calls += 1
    except Exception as exc:  # noqa: BLE001
        state.warnings.append(f"geocode degraded: {exc}")
        state.geometries.append(
            {"name": "aoi_point", "geojson": {"type": "Point", "coordinates": [lon, lat]}}
        )

    buffered = spatial_sql(
        "buffer_point_m",
        {"lon": lon, "lat": lat, "distance_m": 2000},
    )
    state.tool_calls += 1
    if buffered.get("ok"):
        state.geometries.append({"name": "buffer_2km", "geojson": buffered["geojson"]})
        state.evidence.append({"tool": "spatial_sql", "template": "buffer_point_m"})
    return handoff_to(state, "earth-obs", "Geometry ready for imagery analysis")
