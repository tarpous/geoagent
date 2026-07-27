"""Declared tool allowlists for swarm specialists vs single-agent baseline."""

from __future__ import annotations

from geoagent.schemas.handoff import SpecialistName

# Domain tools each peer may call. Handoff tools are separate (transfer_to_*).
SPECIALIST_TOOLS: dict[SpecialistName, frozenset[str]] = {
    "intake": frozenset(),
    "geodata": frozenset({"geocode", "spatial_sql"}),
    "earth-obs": frozenset({"stac_imagery", "landcover_classify", "detect_objects"}),
    "librarian": frozenset({"docs_search"}),
    "cartographer": frozenset({"make_map"}),
    "critic": frozenset(),
}

# Baseline ablation: one agent may call every domain tool; no handoff tools.
BASELINE_TOOLS: frozenset[str] = frozenset().union(*SPECIALIST_TOOLS.values()) | frozenset(
    {
        "geocode",
        "spatial_sql",
        "stac_imagery",
        "landcover_classify",
        "detect_objects",
        "docs_search",
        "make_map",
    }
)


def assert_tool_allowed(agent: SpecialistName, tool: str) -> None:
    allowed = SPECIALIST_TOOLS.get(agent, frozenset())
    if tool not in allowed:
        raise PermissionError(f"tool {tool!r} not allowed for specialist {agent!r}")
