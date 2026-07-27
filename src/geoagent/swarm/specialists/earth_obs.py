"""Earth-observation specialist."""

from __future__ import annotations

from geoagent.tools.detect import detection_summary
from geoagent.tools.landcover import tree_cover_loss_ha
from geoagent.tools.stac_imagery import ndvi_composite_stats
from geoagent.swarm.handoffs import handoff_to
from geoagent.swarm.state import TeamState


def run_earth_obs(state: TeamState) -> TeamState:
    bbox = [23.70, 37.90, 23.80, 38.00]
    if state.aoi == "Thessaloniki":
        bbox = [22.90, 40.60, 23.00, 40.70]

    stats = ndvi_composite_stats(
        bbox=bbox,
        start_date="2023-01-01",
        end_date="2024-12-31",
    )
    state.tool_calls += 1
    state.evidence.append({"tool": "stac_imagery", "result": stats})
    if stats.get("ndvi_mean") is not None:
        state.numbers.append(
            {
                "name": "ndvi_mean",
                "value": float(stats["ndvi_mean"]),
                "unit": "dimensionless",
                "source_tool": "stac_imagery",
            }
        )

    if "tree" in state.question.lower() or "cover" in state.question.lower():
        loss = tree_cover_loss_ha(
            before_scene_id="attica-ringroad-2023-04",
            after_scene_id="attica-ringroad-2024-06",
        )
        state.tool_calls += 1
        state.evidence.append({"tool": "landcover_classify", "result": loss})
        state.numbers.append(
            {
                "name": "tree_cover_loss",
                "value": float(loss["tree_cover_loss_ha"]),
                "unit": "ha",
                "source_tool": "landcover_classify",
            }
        )

    if "vehicle" in state.question.lower() or "detect" in state.question.lower():
        det = detection_summary("attica-ringroad-2024-06")
        state.tool_calls += 1
        state.evidence.append({"tool": "detect_objects", "result": det})
        state.numbers.append(
            {
                "name": "vehicle_count",
                "value": float(det["counts"].get("vehicle", 0)),
                "unit": "count",
                "source_tool": "detect_objects",
            }
        )

    return handoff_to(state, "librarian", "Need citation support from corpus")
