"""MCP server exposing geospatial tools and ask_swarm."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from geoagent.swarm import run_swarm_with_trace
from geoagent.tools import (
    detection_summary,
    docs_search,
    geocode,
    landcover_classify,
    make_map,
    ndvi_composite_stats,
    spatial_sql,
    tree_cover_loss_ha,
)

mcp = FastMCP("geoagent")
_TRACE_STORE: dict[str, dict[str, Any]] = {}


@mcp.tool()
def ask_swarm(question: str) -> str:
    """Run the full geospatial analyst swarm and return FinalAnswer JSON."""
    answer, trace = run_swarm_with_trace(question)
    payload = {
        "final_answer": answer.model_dump(mode="json"),
        "tool_call_parse_rate": trace.tool_call_parse_rate,
        "schema_ok": trace.schema_ok,
        "events": trace.events,
        "trace_id": answer.trace_id,
    }
    _TRACE_STORE[answer.trace_id] = {
        "events": trace.events,
        "handoffs": trace.handoffs,
        "tool_calls": trace.tool_calls,
        "schema_ok": trace.schema_ok,
        "tool_call_parse_rate": trace.tool_call_parse_rate,
    }
    return json.dumps(payload)


@mcp.tool()
def show_trace(trace_id: str) -> str:
    """Return swarm events/handoffs for a prior ask_swarm trace_id."""
    payload = _TRACE_STORE.get(trace_id)
    if payload is None:
        return json.dumps({"ok": False, "error": "unknown_trace_id", "trace_id": trace_id})
    return json.dumps({"ok": True, "trace_id": trace_id, **payload})


@mcp.tool()
def tool_geocode(query: str) -> str:
    result = geocode(query, require_demo_aoi=True, allow_network=False)
    return json.dumps(result.__dict__, default=str)


@mcp.tool()
def tool_spatial_sql(template: str, params_json: str) -> str:
    params: dict[str, Any] = json.loads(params_json)
    return json.dumps(spatial_sql(template, params))  # type: ignore[arg-type]


@mcp.tool()
def tool_ndvi(bbox_json: str, start_date: str, end_date: str) -> str:
    bbox = json.loads(bbox_json)
    return json.dumps(ndvi_composite_stats(bbox=bbox, start_date=start_date, end_date=end_date))


@mcp.tool()
def tool_landcover(scene_id: str) -> str:
    result = landcover_classify(scene_id=scene_id)
    return json.dumps(
        {
            "scene_id": result.scene_id,
            "class_histogram": result.class_histogram,
            "area_ha_by_class": result.area_ha_by_class,
            "backend": result.backend,
        }
    )


@mcp.tool()
def tool_tree_cover_loss(before_scene_id: str, after_scene_id: str) -> str:
    return json.dumps(
        tree_cover_loss_ha(before_scene_id=before_scene_id, after_scene_id=after_scene_id)
    )


@mcp.tool()
def tool_detect(scene_id: str) -> str:
    return json.dumps(detection_summary(scene_id))


@mcp.tool()
def tool_docs_search(query: str) -> str:
    return json.dumps(docs_search(query))


@mcp.tool()
def tool_make_map(layers_json: str, out_dir: str, name: str = "map") -> str:
    from pathlib import Path

    layers = json.loads(layers_json)
    artifacts = make_map(layers, out_dir=Path(out_dir), name=name)
    return json.dumps({k: str(v) for k, v in artifacts.items()})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
