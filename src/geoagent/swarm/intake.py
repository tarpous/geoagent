"""Intake specialist: classify question and seed team state."""

from __future__ import annotations

import re

from geoagent.swarm.handoffs import handoff_to
from geoagent.swarm.state import TeamState

_ATTICA = re.compile(r"attica|athens|ring\s*road", re.I)
_THESS = re.compile(r"thessaloniki|salonika", re.I)
_TREE = re.compile(r"tree\s*cover|ndvi|land\s*cover", re.I)
_DOC = re.compile(r"document|cite|planning|flood", re.I)
_DETECT = re.compile(r"vehicle|building|detect", re.I)


def run_intake(state: TeamState) -> TeamState:
    q = state.question
    if _THESS.search(q):
        state.aoi = "Thessaloniki"
    elif _ATTICA.search(q):
        state.aoi = "Attica"
    else:
        state.aoi = "Attica"

    if _DOC.search(q) and not (_TREE.search(q) or _DETECT.search(q)):
        return handoff_to(state, "librarian", "Document evidence required", aoi=state.aoi)
    if _TREE.search(q) or _DETECT.search(q) or _ATTICA.search(q) or _THESS.search(q):
        return handoff_to(state, "geodata", "Need AOI geometry before analysis", aoi=state.aoi)
    return handoff_to(state, "geodata", "Spatial context required", aoi=state.aoi)
