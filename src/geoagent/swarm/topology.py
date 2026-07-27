"""Engineered swarm topology: allowed peer handoffs (not a supervisor).

This is graph engineering for the specialist network: nodes, directed edges,
and optional parallel join phases. Runtime peers pick among *allowed* edges;
they do not call a manager, matching the project's langgraph-swarm thesis.

Kimi Agent Swarm (commander + mass parallel spawn) is intentionally out of
scope — that is a hierarchical/orchestrator pattern, which this repo forbids.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from geoagent.schemas.handoff import SpecialistName

# Critic may bounce to peers once (bounded reflection); otherwise terminal.
SWARM_EDGES: dict[SpecialistName, frozenset[SpecialistName]] = {
    "intake": frozenset({"geodata", "librarian", "critic"}),
    "geodata": frozenset({"earth-obs", "librarian", "cartographer", "critic"}),
    "earth-obs": frozenset({"librarian", "cartographer", "geodata", "critic"}),
    "librarian": frozenset({"cartographer", "earth-obs", "geodata", "critic"}),
    "cartographer": frozenset({"critic", "librarian", "earth-obs"}),
    "critic": frozenset({"geodata", "earth-obs", "librarian", "cartographer"}),
}

# After geodata, these peers may run as a parallel join phase when both are needed.
PARALLEL_AFTER_GEODATA: frozenset[SpecialistName] = frozenset({"earth-obs", "librarian"})

SPECIALISTS: tuple[SpecialistName, ...] = (
    "intake",
    "geodata",
    "earth-obs",
    "librarian",
    "cartographer",
    "critic",
)


@dataclass(frozen=True)
class SwarmTopology:
    """Compile-time handoff graph for the specialist swarm."""

    edges: dict[SpecialistName, frozenset[SpecialistName]] = field(
        default_factory=lambda: dict(SWARM_EDGES)
    )
    parallel_after_geodata: frozenset[SpecialistName] = PARALLEL_AFTER_GEODATA

    def allowed(self, src: SpecialistName) -> frozenset[SpecialistName]:
        return self.edges.get(src, frozenset())

    def is_allowed(self, src: SpecialistName, dst: SpecialistName) -> bool:
        return dst in self.allowed(src)

    def assert_allowed(self, src: SpecialistName, dst: SpecialistName) -> None:
        if not self.is_allowed(src, dst):
            raise ValueError(f"handoff {src!r} → {dst!r} not in swarm topology")

    def as_adjacency(self) -> dict[str, list[str]]:
        return {k: sorted(v) for k, v in self.edges.items()}


DEFAULT_TOPOLOGY = SwarmTopology()


def validate_handoff_edge(
    src: SpecialistName,
    dst: SpecialistName,
    *,
    topology: SwarmTopology | None = None,
) -> bool:
    topo = topology or DEFAULT_TOPOLOGY
    return topo.is_allowed(src, dst)
