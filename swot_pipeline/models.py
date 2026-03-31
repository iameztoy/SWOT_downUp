from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AOIConfig:
    bbox: tuple[float, float, float, float] | None = None
    polygon_path: Path | None = None
    polygon_wkt: str | None = None
    geojson: dict[str, Any] | None = None
    method: str = "bbox"  # bbox | polygon | geojson | wkt | shapefile | preset
    preset_id: str | None = None
    saved_aoi_id: str | None = None


@dataclass
class DateRangeConfig:
    start: datetime
    end: datetime


@dataclass
class DataAccessConfig:
    mode: str
    short_name: str
    version: str | None = None
    provider: str = "POCLOUD"
    output_dir: Path = Path("data/raw")
    page_size: int = 200
    max_results: int | None = None
    podaac_downloader_cmd: str = "podaac-data-downloader"
    podaac_subscriber_cmd: str = "podaac-data-subscriber"
    downloader_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessConfig:
    output_dir: Path = Path("data/processed")
    output_mode: str = "ee_ready"  # ee_ready | native_utm
    write_cog: bool = True
    include_qa_masks: bool = True
    nodata: float = -9999.0
    variables: list[str] = field(default_factory=list)
    optional_variables: list[str] = field(default_factory=list)
    quality_rules: dict[str, Any] = field(default_factory=dict)
    workflow_step: str = "full"  # raw_only | extract | qa | full
    write_filtered_band: bool = False


@dataclass
class PublishConfig:
    enabled: bool = False
    gcs_bucket: str | None = None
    gcs_prefix: str = "swot"
    ee_asset_root: str | None = None
    ee_collection_root: str | None = None
    ee_mode: str = "ingested"  # ingested | external_image
    project_id: str | None = None
    task_poll_interval_s: int = 20
    task_timeout_s: int = 1800
    write_asset_properties: bool = True
    publish_immediately: bool = True


@dataclass
class AuthConfig:
    earthdata_username: str | None = None
    earthdata_password: str | None = None
    netrc_path: Path | None = None
    gcp_credentials_path: Path | None = None
    ee_service_account: str | None = None
    ee_private_key_path: Path | None = None
    use_env: bool = True


@dataclass
class ProductPluginConfig:
    plugin: str
    short_name: str
    version: str | None = None
    variable_map: dict[str, str] = field(default_factory=dict)
    preferred_output_bands: list[str] = field(default_factory=list)
    native_epsg: int | None = None
    latitude_var: str = "latitude"
    longitude_var: str = "longitude"
    x_var: str = "x"
    y_var: str = "y"
    downloader_compatibility: list[str] = field(default_factory=list)
    ui_defaults: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkingConfig:
    enabled: bool = True
    mode: str = "auto"  # auto | always | never
    max_tile_area_km2: float = 300_000.0
    max_tile_span_deg: float = 8.0
    max_tiles: int = 400


@dataclass
class PipelineConfig:
    date_range: DateRangeConfig
    aoi: AOIConfig
    data_access: DataAccessConfig
    process: ProcessConfig
    publish: PublishConfig
    auth: AuthConfig
    product: ProductPluginConfig
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    run_label: str | None = None


@dataclass
class GranuleRecord:
    granule_id: str
    url: str
    filename: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    local_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedRaster:
    source_granule: GranuleRecord
    local_path: Path
    bands: list[str]
    acquisition_time: datetime
    mode: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    asset_id: str
    task_id: str
    state: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkPlan:
    index: int
    bbox: tuple[float, float, float, float]
    area_km2: float
    label: str


@dataclass
class JobSummary:
    job_id: str
    status: str
    created_at: str
    updated_at: str
    message: str | None = None
