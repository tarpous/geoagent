"""Swarm step / tool-call budgets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class Budgets:
    max_tool_calls_per_specialist: int = 8
    max_swarm_steps: int = 24
    structured_output_repair_retries: int = 1


def load_budgets(config_path: Path | None = None) -> Budgets:
    path = config_path or Path(__file__).resolve().parents[3] / "configs" / "models.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    raw = data.get("budgets", {})
    return Budgets(
        max_tool_calls_per_specialist=int(raw.get("max_tool_calls_per_specialist", 8)),
        max_swarm_steps=int(raw.get("max_swarm_steps", 24)),
        structured_output_repair_retries=int(raw.get("structured_output_repair_retries", 1)),
    )
