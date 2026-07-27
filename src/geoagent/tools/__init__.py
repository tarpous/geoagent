"""Geospatial tools package."""

from geoagent.tools.detect import detect_objects, detection_summary
from geoagent.tools.docs_search import docs_search
from geoagent.tools.geocode import GeocodeResult, geocode
from geoagent.tools.landcover import landcover_classify, tree_cover_loss_ha
from geoagent.tools.mapping import make_map
from geoagent.tools.spatial_sql import spatial_sql
from geoagent.tools.stac_imagery import ndvi_composite_stats, search_imagery

__all__ = [
    "GeocodeResult",
    "detect_objects",
    "detection_summary",
    "docs_search",
    "geocode",
    "landcover_classify",
    "make_map",
    "ndvi_composite_stats",
    "search_imagery",
    "spatial_sql",
    "tree_cover_loss_ha",
]
