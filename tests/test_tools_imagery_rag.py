"""STAC / NDVI / landcover / detect / docs_search tests."""

from __future__ import annotations

from geoagent.tools import (
    detection_summary,
    docs_search,
    landcover_classify,
    ndvi_composite_stats,
    search_imagery,
    tree_cover_loss_ha,
)


def test_stac_fixture_search_and_ndvi():
    scenes = search_imagery(
        bbox=[23.71, 37.91, 23.79, 37.99],
        start_date="2023-01-01",
        end_date="2024-12-31",
        live=False,
    )
    assert scenes
    assert all(s.source == "fixture" for s in scenes)
    stats = ndvi_composite_stats(
        bbox=[23.71, 37.91, 23.79, 37.99],
        start_date="2023-01-01",
        end_date="2024-12-31",
    )
    assert stats["ok"] is True
    assert stats["ndvi_mean"] is not None


def test_landcover_histogram_and_tree_loss():
    result = landcover_classify(scene_id="attica-ringroad-2023-04")
    assert result.class_histogram
    assert abs(sum(result.class_histogram.values()) - 1.0) < 1e-6
    assert result.class_histogram["tree"] > 0
    loss = tree_cover_loss_ha(
        before_scene_id="attica-ringroad-2023-04",
        after_scene_id="attica-ringroad-2024-06",
    )
    assert loss["ok"] is True
    assert loss["tree_cover_loss_ha"] >= 0


def test_detect_objects_known_positives():
    summary = detection_summary("attica-ringroad-2024-06")
    assert summary["ok"] is True
    assert summary["counts"]["vehicle"] >= 1
    assert summary["counts"]["building"] >= 1


def test_docs_search_returns_citations():
    result = docs_search("tree cover loss near ring road", prefer_postgres=True)
    assert result["ok"] is True
    assert result["evidence"]
    cite = result["evidence"][0]["citation"]
    assert cite["doc_id"]
    assert cite["quote"] or cite["span_start"] is not None
