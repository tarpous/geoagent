from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_locked_demo_roster_present():
    text = (ROOT / "configs" / "models.yaml").read_text(encoding="utf-8")
    assert "Qwen3.5-9B" in text
    assert "Gemma-4-E4B" in text
    assert "Attica" in text
    assert "Thessaloniki" in text


def test_corpus_manifest_has_license_columns():
    header = (ROOT / "data" / "corpus_manifest.csv").read_text(encoding="utf-8").splitlines()[0]
    for col in ("doc_id", "license", "source_url", "retrieval_date"):
        assert col in header


def test_notice_and_osm_attribution_exist():
    assert (ROOT / "NOTICE").is_file()
    assert (ROOT / "data" / "osm" / "ATTRIBUTION").is_file()
