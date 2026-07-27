"""Swarm hero-path smoke test."""

from geoagent.swarm import run_swarm

HERO = "How much tree cover was lost within 2 km of the new ring road since 2023?"


def test_swarm_hero_path_returns_final_answer():
    answer = run_swarm(HERO)
    assert answer.status in {"answered", "degraded"}
    assert answer.answer_md
    loss = next(n for n in answer.numbers if n.name == "tree_cover_loss")
    assert loss.unit == "ha"
    assert loss.value >= 0
    assert answer.citations or answer.warnings
