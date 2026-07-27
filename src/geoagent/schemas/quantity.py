"""Quantity values with explicit units."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Unit = Literal[
    "m",
    "km",
    "m2",
    "ha",
    "percent",
    "count",
    "deg",
    "dimensionless",
]


class Quantity(BaseModel):
    """A named numeric measurement with an explicit unit and provenance."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    value: float
    unit: Unit
    source_tool: str = Field(min_length=1)
    ci: tuple[float, float] | None = None
