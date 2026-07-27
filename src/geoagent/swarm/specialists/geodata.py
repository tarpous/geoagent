"""Geodata specialist."""

from __future__ import annotations

from geoagent.swarm.policy import transfer_control
from geoagent.swarm.state import TeamState
from geoagent.swarm.tool_allowlists import assert_tool_allowed
from geoagent.tools.geocode import geocode
from geoagent.tools.spatial_sql import spatial_sql

_AOI_POINTS = {
    "Attica": (23.72, 37.98, "Athens Attica Greece"),
    "Thessaloniki": (22.94, 40.64, "Thessaloniki Greece"),
}


def work_geodata(state: TeamState) -> TeamState:
    aoi = state.aoi or "Attica"
    lon, lat, place = _AOI_POINTS.get(aoi, _AOI_POINTS["Attica"])
    assert_tool_allowed("geodata", "geocode")
    try:
        geo = geocode(place, require_demo_aoi=True, allow_network=False)
        lon, lat = geo.lon, geo.lat
        state.evidence.append({"tool": "geocode", "display_name": geo.display_name})
        state.geometries.append({"name": "geocode", "geojson": geo.geojson})
        state.tool_calls += 1
    except Exception as exc:  # noqa: BLE001
        state.warnings.append(f"geocode degraded: {exc}")
        state.geometries.append(
            {"name": "aoi_point", "geojson": {"type": "Point", "coordinates": [lon, lat]}}
        )

    assert_tool_allowed("geodata", "spatial_sql")
    buffered = spatial_sql(
        "buffer_point_m",
        {"lon": lon, "lat": lat, "distance_m": 2000},
    )
    state.tool_calls += 1
    if buffered.get("ok"):
        state.geometries.append({"name": "buffer_2km", "geojson": buffered["geojson"]})
        state.evidence.append(
            {
                "tool": "spatial_sql",
                "template": "buffer_point_m",
                "backend": buffered.get("backend"),
            }
        )

    if "ring" in state.question.lower() or "road" in state.question.lower():
        roads = spatial_sql(
            "roads_near_point",
            {"lon": lon, "lat": lat, "distance_m": 2000},
        )
        state.tool_calls += 1
        if roads.get("ok"):
            state.evidence.append(
                {
                    "tool": "spatial_sql",
                    "template": "roads_near_point",
                    "count": roads.get("count"),
                    "attribution": roads.get("attribution"),
                }
            )
            if roads.get("geojson"):
                state.geometries.append({"name": "roads_near", "geojson": roads["geojson"]})
    return state


def run_geodata(state: TeamState, *, transfer: bool = True) -> TeamState:
    state = work_geodata(state)
    if not transfer:
        if state.active_agent not in state.visited_agents:
            state.visited_agents.append(state.active_agent)
        return state
    return transfer_control(state, from_agent="geodata")
