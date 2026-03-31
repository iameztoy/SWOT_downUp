from app.services.aoi_service import validate_aoi
from swot_pipeline.models import ChunkingConfig


def test_validate_aoi_bbox_returns_summary():
    summary = validate_aoi({"method": "bbox", "bbox": [-5, 40, 5, 45]})
    assert summary["is_valid"] is True
    assert summary["area_km2"] > 0
    assert len(summary["bbox"]) == 4


def test_validate_aoi_large_extent_with_chunking():
    summary = validate_aoi(
        {"method": "bbox", "bbox": [-25, 0, 45, 55]},
        chunking=ChunkingConfig(enabled=True, mode="always", max_tile_area_km2=120000, max_tile_span_deg=5, max_tiles=500),
    )
    assert summary["chunk_count"] > 1
    assert isinstance(summary["chunks_preview"], list)
