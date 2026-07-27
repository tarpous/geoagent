"""Swarm execution traces and schema/tool-call metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from geoagent.schemas.answer import FinalAnswer
from geoagent.schemas.events import StreamEvent
from geoagent.schemas.handoff import Handoff


@dataclass(slots=True)
class TraceRecord:
    trace_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    final_answer: dict[str, Any] | None = None
    schema_ok: bool = False
    tool_call_parse_ok: int = 0
    tool_call_parse_total: int = 0

    @property
    def tool_call_parse_rate(self) -> float:
        if self.tool_call_parse_total == 0:
            return 1.0
        return self.tool_call_parse_ok / self.tool_call_parse_total

    def add_event(self, event: StreamEvent) -> None:
        self.events.append(event.model_dump())

    def add_handoff(self, handoff: Handoff) -> None:
        self.handoffs.append(handoff.model_dump())
        self.add_event(
            StreamEvent(
                type="handoff",
                trace_id=self.trace_id,
                agent=None,
                payload=handoff.model_dump(),
            )
        )

    def add_tool_call(self, agent: str, tool: str, payload: dict[str, Any], *, ok: bool) -> None:
        self.tool_calls.append({"agent": agent, "tool": tool, "ok": ok, "payload": payload})
        self.tool_call_parse_total += 1
        if ok:
            self.tool_call_parse_ok += 1
        self.add_event(
            StreamEvent(
                type="tool_call" if ok else "warning",
                trace_id=self.trace_id,
                agent=agent,
                payload={"tool": tool, "ok": ok, **payload},
            )
        )

    def finalize(self, answer: FinalAnswer) -> None:
        try:
            FinalAnswer.model_validate(answer.model_dump(mode="json"))
            self.schema_ok = True
        except ValidationError:
            self.schema_ok = False
        self.final_answer = answer.model_dump(mode="json")
        self.add_event(
            StreamEvent(
                type="done",
                trace_id=self.trace_id,
                agent="critic",
                payload={"status": answer.status, "schema_ok": self.schema_ok},
            )
        )

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "trace_id": self.trace_id,
                    "schema_ok": self.schema_ok,
                    "tool_call_parse_rate": self.tool_call_parse_rate,
                    "handoffs": self.handoffs,
                    "tool_calls": self.tool_calls,
                    "events": self.events,
                    "final_answer": self.final_answer,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
