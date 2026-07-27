"""Tests for M4 golden factory, judge, calibration, and M5 ablation."""

from evals.calibrate import calibrate_from_audit, cohens_kappa
from evals.factory.golden_v1 import build_audit_slice, build_golden_v1
from evals.judge import run_judge
from evals.run_ablation import run_ablation

from geoagent.baseline import run_single_agent


def test_golden_v1_has_at_least_80_items():
    items = build_golden_v1(100)
    assert len(items) >= 80
    assert all(i.version == "golden@v1" for i in items)
    audit = build_audit_slice(items, 25)
    assert 20 <= len(audit) <= 30


def test_kappa_and_calibration_smoke():
    assert cohens_kappa(["answered", "refused"], ["answered", "refused"]) == 1.0
    report = calibrate_from_audit()
    assert report["n"] >= 20
    assert "kappa" in report


def test_judge_and_ablation_and_single_agent():
    single = run_single_agent(
        "How much tree cover was lost within 2 km of the new ring road since 2023?"
    )
    assert any(n.name == "tree_cover_loss" for n in single.numbers)
    judge = run_judge(mode="swarm", limit=8)
    assert judge["n"] == 8
    ablation = run_ablation(
        [
            "How much tree cover was lost within 2 km of the new ring road since 2023?",
            "Count vehicles visible on a cached Attica tile.",
        ]
    )
    assert ablation["n"] == 2
    assert "swarm_mean_score" in ablation
