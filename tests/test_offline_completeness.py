"""Offline mapping, geocode fixtures, prompts, and tool allowlists."""

from __future__ import annotations

from pathlib import Path

import pytest

from geoagent.prompts import available_prompts, load_prompt
from geoagent.swarm.tool_allowlists import BASELINE_TOOLS, SPECIALIST_TOOLS, assert_tool_allowed
from geoagent.tools.geocode import geocode
from geoagent.tools.mapping import make_map


def test_geocode_offline_fixture(tmp_path: Path):
    from geoagent.tools.geocode import GeocodeCache

    cache = GeocodeCache(tmp_path / "empty.json")
    result = geocode("Athens Attica Greece", cache=cache, allow_network=False)
    assert result.backend == "fixture"
    assert 23.0 < result.lon < 24.5


def test_make_map_writes_html_and_png(tmp_path: Path):
    arts = make_map(
        [{"name": "pt", "geojson": {"type": "Point", "coordinates": [23.72, 37.98]}}],
        out_dir=tmp_path,
        name="demo",
    )
    assert arts["geojson"].is_file()
    assert arts["html"].is_file()
    assert arts["png"].is_file()
    assert arts["png"].stat().st_size > 50


def test_prompts_load():
    roles = available_prompts()
    assert "intake" in roles and "critic" in roles
    text = load_prompt("geodata")
    assert "Geodata" in text or "geodata" in text.lower()


def test_specialist_tool_allowlists():
    assert "geocode" in SPECIALIST_TOOLS["geodata"]
    assert "docs_search" not in SPECIALIST_TOOLS["geodata"]
    assert "make_map" in BASELINE_TOOLS
    assert_tool_allowed("librarian", "docs_search")
    with pytest.raises(PermissionError):
        assert_tool_allowed("librarian", "geocode")
