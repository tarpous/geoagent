# Fixture markers

This directory will hold committed offline CI fixtures:

- clipped OSM extracts for Attica and Thessaloniki
- cached Sentinel-2 tiles / NDVI composites
- sample corpus PDFs referenced by `data/corpus_manifest.csv`

Fixtures accelerate offline CI. They do not replace real tool implementations or model inference.

## Imagery

`data/fixtures/imagery/` holds synthetic Sentinel-2-like band grids and detection
labels used by `stac_imagery`, `landcover_classify`, and `detect_objects` until
pinned ONNX/STAC caches are downloaded.
