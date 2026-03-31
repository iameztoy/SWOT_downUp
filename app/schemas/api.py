from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class AOIValidateRequest(BaseModel):
    method: str = "bbox"
    bbox: list[float] | None = None
    wkt: str | None = None
    geojson: dict[str, Any] | None = None
    preset_id: str | None = None
    zip_path: str | None = None
    chunking_enabled: bool = True
    chunking_mode: str = "auto"
    max_tile_area_km2: float = 300000.0
    max_tile_span_deg: float = 8.0
    max_tiles: int = 400


class AOIValidateResponse(BaseModel):
    is_valid: bool
    bbox: list[float]
    area_km2: float
    size_class: str
    chunk_count: int
    chunks_preview: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    geometry_geojson: dict[str, Any]
    crs: str = "EPSG:4326"


class ConfigPreviewRequest(BaseModel):
    config: dict[str, Any]


class ConfigPreviewResponse(BaseModel):
    normalized_config: dict[str, Any]
    yaml: str
    warnings: list[str] = Field(default_factory=list)


class JobCreateRequest(BaseModel):
    config: dict[str, Any]


class JobCreateResponse(BaseModel):
    id: str
    status: str


class JobDetailsResponse(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: str
    progress: float
    message: str | None = None
    error: str | None = None
    config: dict[str, Any]


class JobsListResponse(BaseModel):
    jobs: list[JobDetailsResponse]


class JobLogsResponse(BaseModel):
    logs: list[dict[str, Any]]


class JobOutputsResponse(BaseModel):
    outputs: list[dict[str, Any]]


class SaveAOIRequest(BaseModel):
    id: str
    name: str
    method: str
    geometry: dict[str, Any]


class SaveAOIResponse(BaseModel):
    id: str
    name: str


class SavedAOIsResponse(BaseModel):
    aois: list[dict[str, Any]]
