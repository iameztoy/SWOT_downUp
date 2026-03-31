from __future__ import annotations

from typing import Any

from swot_pipeline.aoi import chunk_geometry, geometry_summary, parse_aoi_payload, preset_regions
from swot_pipeline.models import ChunkingConfig


def validate_aoi(payload: dict[str, Any], chunking: ChunkingConfig | None = None) -> dict[str, Any]:
    geom = parse_aoi_payload(payload)
    summary = geometry_summary(geom)

    chunk_cfg = chunking or ChunkingConfig()
    should_chunk = False
    if chunk_cfg.enabled:
        if chunk_cfg.mode == "always":
            should_chunk = True
        elif chunk_cfg.mode == "auto" and summary["size_class"] == "large":
            should_chunk = True

    if should_chunk:
        chunks = chunk_geometry(
            geom,
            max_tile_area_km2=chunk_cfg.max_tile_area_km2,
            max_tile_span_deg=chunk_cfg.max_tile_span_deg,
            max_tiles=chunk_cfg.max_tiles,
        )
    else:
        chunks = []

    summary["chunk_count"] = max(1, len(chunks))
    summary["chunks_preview"] = [
        {
            "label": c.label,
            "bbox": list(c.bbox),
            "area_km2": c.area_km2,
        }
        for c in chunks[:12]
    ]
    return summary


def get_presets() -> list[dict[str, Any]]:
    return preset_regions()
