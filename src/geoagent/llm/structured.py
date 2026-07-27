"""Schema-validated structured output with one repair retry."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

Emitter = Callable[[str, dict[str, Any] | None], str]


class StructuredOutputError(RuntimeError):
    """Raised after the allowed repair retry is exhausted."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


def parse_model(model_type: type[T], payload: str | dict[str, Any]) -> T:
    if isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload
    return model_type.model_validate(data)


def generate_structured(
    model_type: type[T],
    *,
    emit: Emitter,
    prompt: str,
    max_repair_retries: int = 1,
) -> T:
    """Request structured JSON, validate, and allow one repair retry."""
    raw = emit(prompt, None)
    last_error: str | None = None

    for attempt in range(max_repair_retries + 1):
        try:
            return parse_model(model_type, raw)
        except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
            last_error = str(exc)
            if attempt >= max_repair_retries:
                break
            repair_prompt = (
                f"{prompt}\n\n"
                "Previous output failed schema validation. "
                f"Return corrected JSON only.\nValidator error:\n{last_error}"
            )
            raw = emit(repair_prompt, {"repair": True, "error": last_error})

    raise StructuredOutputError(
        "schema_violation",
        detail=last_error,
    )


def tool_schema_failure(detail: str) -> dict[str, Any]:
    """Controlled tool failure payload (never crash the swarm)."""
    return {"ok": False, "error": "schema_violation", "detail": detail}
