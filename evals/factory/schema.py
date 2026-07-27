"""Golden-item schema for the eval factory."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ItemKind = Literal[
    "spatial",
    "imagery",
    "rag",
    "multi_tool",
    "refusal",
    "injection",
]


class GoldenItem(BaseModel):
    """One machine-authored eval item destined for evals/golden/*.jsonl."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    version: str = "golden@v1"
    kind: ItemKind
    question: str = Field(min_length=1)
    aoi: str | None = None
    expects_tools: list[str] = Field(default_factory=list)
    expects_status: Literal["answered", "refused", "degraded"] = "answered"
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
