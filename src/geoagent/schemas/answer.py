"""FinalAnswer and related answer contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from geoagent.schemas.quantity import Quantity

AnswerStatus = Literal["answered", "refused", "degraded"]
RefusalReasonCode = Literal[
    "unanswerable",
    "out_of_aoi",
    "unsafe",
    "budget",
    "tool_failure",
]


class Citation(BaseModel):
    """Span- or quote-level document citation."""

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    span_start: int | None = None
    span_end: int | None = None
    quote: str | None = Field(default=None, max_length=300)
    uri: str | None = None
    page: int | None = None

    @model_validator(mode="after")
    def require_span_or_quote(self) -> Citation:
        has_span = self.span_start is not None and self.span_end is not None
        has_quote = bool(self.quote and self.quote.strip())
        if not has_span and not has_quote:
            raise ValueError("citation requires span_start/span_end or a non-empty quote")
        if has_span and self.span_end is not None and self.span_start is not None:
            if self.span_end < self.span_start:
                raise ValueError("span_end must be >= span_start")
        return self


class GeoRef(BaseModel):
    """WGS84 GeoJSON geometry reference produced or used by the swarm."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    geojson: dict[str, Any]
    epsg_computed: str | None = None

    @field_validator("geojson")
    @classmethod
    def require_geojson_type(cls, value: dict[str, Any]) -> dict[str, Any]:
        if "type" not in value:
            raise ValueError("geojson must include a type field")
        return value


class Refusal(BaseModel):
    """Structured refusal payload when status is refused."""

    model_config = ConfigDict(extra="forbid")

    reason_code: RefusalReasonCode
    message: str = Field(min_length=1)


class FinalAnswer(BaseModel):
    """Single turn result consumed by critic, TUI, web UI, MCP, and evals."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1)
    status: AnswerStatus
    answer_md: str = ""
    numbers: list[Quantity] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    geometries: list[GeoRef] = Field(default_factory=list)
    map_artifact: Path | None = None
    refusal: Refusal | None = None
    warnings: list[str] = Field(default_factory=list)
    model_roster: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_invariants(self) -> FinalAnswer:
        if self.status == "refused":
            if self.answer_md.strip():
                raise ValueError("refused answers must have empty answer_md")
            if self.refusal is None:
                raise ValueError("refused answers require a refusal payload")
        elif self.refusal is not None:
            raise ValueError("refusal is only allowed when status is refused")
        elif not self.answer_md.strip():
            raise ValueError("answered/degraded answers require non-empty answer_md")
        return self
