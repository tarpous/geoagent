"""Structured-output repair-path tests."""

from __future__ import annotations

import json

import pytest

from geoagent.llm import StructuredOutputError, generate_structured, tool_schema_failure
from geoagent.llm.provider import load_role_config
from geoagent.schemas import Quantity


def test_generate_structured_repairs_once():
    calls: list[str] = []

    def emit(prompt: str, meta: dict | None) -> str:
        calls.append(prompt)
        if meta and meta.get("repair"):
            return json.dumps(
                {
                    "name": "area",
                    "value": 12.5,
                    "unit": "ha",
                    "source_tool": "landcover_classify",
                }
            )
        return '{"name": "area", "value": "bad", "unit": "ha", "source_tool": "x"}'

    qty = generate_structured(Quantity, emit=emit, prompt="emit quantity json")
    assert qty.value == 12.5
    assert len(calls) == 2


def test_generate_structured_fails_after_one_repair():
    def emit(prompt: str, meta: dict | None) -> str:
        return '{"name": "area"}'

    with pytest.raises(StructuredOutputError) as exc:
        generate_structured(Quantity, emit=emit, prompt="emit quantity json")
    assert exc.value.args[0] == "schema_violation"
    assert tool_schema_failure("boom")["ok"] is False


def test_load_role_config_demo_intake():
    cfg = load_role_config("intake")
    assert cfg.backend == "llamacpp"
    assert "Qwen3.5-9B" in cfg.model
    assert "Q4_K_M" in cfg.model
