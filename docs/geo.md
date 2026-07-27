# Geospatial correctness

Executable rules (enforced in `tests/geo/` and tool wrappers):

| Rule | Implementation |
|---|---|
| Storage CRS | Persist/exchange geometries as EPSG:4326 (WGS84) lon/lat |
| Metric work | Buffers, lengths, areas in a projected CRS (default EPSG:2100 for Greece demo AOIs) |
| Units | Tools return explicit units; `Quantity.unit` must match the tool contract |
| Geometry sanity | Reject empty, NaN, non-finite coords; bbox must intersect demo AOIs unless opted out |
| Time | Imagery/stats declare timezone (UTC) and inclusive date bounds |

The critic calls these validators; it does not re-implement geo math in prose.
