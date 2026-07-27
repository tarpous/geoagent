"""Cartographer specialist."""

from __future__ import annotations

from pathlib import Path

from geoagent.tools.mapping import make_map
from geoagent.swarm.handoffs import handoff_to
from geoagent.swarm.state import TeamState

ROOT = Path(__file__).resolve().parents[4]


def run_cartographer(state: TeamState) -> TeamState:
    out_dir = ROOT / "artifacts" / "demo" / state.trace_id
    layers = [{"name": g.get("name", "layer"), "geojson": g["geojson"]} for g in state.geometries if "geojson" in g]
    if not layers:
        layers = [
            {
                "name": "attica",
                "geojson": {"type": "Point", "coordinates": [23.72, 37.98]},
            }
        ]
    artifacts = make_map(layers, out_dir=out_dir, name="map")
    state.tool_calls += 1
    state.evidence.append(
        {
            "tool": "make_map",
            "artifacts": {k: str(v) for k, v in artifacts.items()},
        }
    )
    loss = next((n for n in state.numbers if n.get("name") == "tree_cover_loss"), None)
    if loss:
        state.draft_answer_md = (
            f"Estimated tree-cover loss near the ring-road corridor is "
            f"{loss['value']:.2f} {loss['unit']} based on fixture land-cover change "
            f"between 2023 and 2024 scenes, with supporting document citations."
        )
    else:
        state.draft_answer_md = (
            "Assembled geospatial evidence for the question using spatial, imagery, "
            "and document tools. See numbers and citations in the structured answer."
        )
    return handoff_to(state, "critic", "Draft ready for validation")
