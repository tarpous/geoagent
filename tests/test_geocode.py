"""Offline geocode cache tests (no live Nominatim call)."""

from pathlib import Path

from geoagent.tools.geocode import GeocodeCache, geocode


def test_geocode_uses_cache(tmp_path: Path):
    cache_path = tmp_path / "geocode.json"
    cache = GeocodeCache(cache_path)
    cache.set(
        "Port of Thessaloniki",
        {
            "display_name": "Port of Thessaloniki",
            "lon": 22.935,
            "lat": 40.635,
        },
    )
    result = geocode("Port of Thessaloniki", cache=cache, require_demo_aoi=True)
    assert result.lon == 22.935
    assert result.geojson["type"] == "Point"
