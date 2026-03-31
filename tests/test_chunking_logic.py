from shapely.geometry import box

from swot_pipeline.aoi.service import chunk_geometry


def test_large_aoi_chunking_produces_multiple_tiles():
    geom = box(-20, 0, 40, 45)
    chunks = chunk_geometry(
        geom,
        max_tile_area_km2=100000,
        max_tile_span_deg=5,
        max_tiles=200,
    )
    assert len(chunks) > 1
    assert all(len(c.bbox) == 4 for c in chunks)
