"""Eval factory seed tests."""

from __future__ import annotations

from evals.factory.seed import build_seed_items
from geoagent.swarm.budget import load_budgets


def test_factory_emits_at_least_ten_valid_items():
    items = build_seed_items()
    assert len(items) >= 10
    assert all(item.version == "golden@v1" for item in items)
    assert any(item.id.endswith("tree-loss") or "tree" in item.question.lower() for item in items)


def test_budgets_from_config():
    budgets = load_budgets()
    assert budgets.max_tool_calls_per_specialist == 8
    assert budgets.structured_output_repair_retries == 1
