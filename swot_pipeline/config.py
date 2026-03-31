from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from swot_pipeline.models import (
    AOIConfig,
    AuthConfig,
    ChunkingConfig,
    DataAccessConfig,
    DateRangeConfig,
    PipelineConfig,
    ProcessConfig,
    ProductPluginConfig,
    PublishConfig,
)


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _as_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def load_config(path: str | Path) -> PipelineConfig:
    cfg_path = Path(path)
    raw = yaml.safe_load(cfg_path.read_text())
    return parse_config_dict(raw)


def parse_config_dict(raw: dict[str, Any]) -> PipelineConfig:
    date_range = DateRangeConfig(
        start=_parse_datetime(raw["date_range"]["start"]),
        end=_parse_datetime(raw["date_range"]["end"]),
    )

    aoi_raw = raw.get("aoi", {})
    bbox = tuple(aoi_raw["bbox"]) if aoi_raw.get("bbox") else None
    aoi = AOIConfig(
        bbox=bbox,
        polygon_path=_as_path(aoi_raw.get("polygon_path")),
        polygon_wkt=aoi_raw.get("polygon_wkt"),
        geojson=aoi_raw.get("geojson"),
        method=aoi_raw.get("method", "bbox"),
        preset_id=aoi_raw.get("preset_id"),
        saved_aoi_id=aoi_raw.get("saved_aoi_id"),
    )

    da_raw = raw["data_access"]
    data_access = DataAccessConfig(
        mode=da_raw["mode"],
        short_name=da_raw["short_name"],
        version=da_raw.get("version"),
        provider=da_raw.get("provider", "POCLOUD"),
        output_dir=Path(da_raw.get("output_dir", "data/raw")),
        page_size=da_raw.get("page_size", 200),
        max_results=da_raw.get("max_results"),
        podaac_downloader_cmd=da_raw.get("podaac_downloader_cmd", "podaac-data-downloader"),
        podaac_subscriber_cmd=da_raw.get("podaac_subscriber_cmd", "podaac-data-subscriber"),
        downloader_options=da_raw.get("downloader_options", {}),
    )

    process_raw = raw.get("process", {})
    process = ProcessConfig(
        output_dir=Path(process_raw.get("output_dir", "data/processed")),
        output_mode=process_raw.get("output_mode", "ee_ready"),
        write_cog=process_raw.get("write_cog", True),
        include_qa_masks=process_raw.get("include_qa_masks", True),
        nodata=process_raw.get("nodata", -9999.0),
        variables=process_raw.get("variables", []),
        optional_variables=process_raw.get("optional_variables", []),
        quality_rules=process_raw.get("quality_rules", {}),
        workflow_step=process_raw.get("workflow_step", "full"),
        write_filtered_band=process_raw.get("write_filtered_band", False),
    )

    publish_raw = raw.get("publish", {})
    publish = PublishConfig(
        enabled=publish_raw.get("enabled", False),
        gcs_bucket=publish_raw.get("gcs_bucket"),
        gcs_prefix=publish_raw.get("gcs_prefix", "swot"),
        ee_asset_root=publish_raw.get("ee_asset_root"),
        ee_collection_root=publish_raw.get("ee_collection_root"),
        ee_mode=publish_raw.get("ee_mode", "ingested"),
        project_id=publish_raw.get("project_id"),
        task_poll_interval_s=publish_raw.get("task_poll_interval_s", 20),
        task_timeout_s=publish_raw.get("task_timeout_s", 1800),
        write_asset_properties=publish_raw.get("write_asset_properties", True),
        publish_immediately=publish_raw.get("publish_immediately", True),
    )

    auth_raw = raw.get("auth", {})
    auth = AuthConfig(
        earthdata_username=auth_raw.get("earthdata_username"),
        earthdata_password=auth_raw.get("earthdata_password"),
        netrc_path=_as_path(auth_raw.get("netrc_path")),
        gcp_credentials_path=_as_path(auth_raw.get("gcp_credentials_path")),
        ee_service_account=auth_raw.get("ee_service_account"),
        ee_private_key_path=_as_path(auth_raw.get("ee_private_key_path")),
        use_env=auth_raw.get("use_env", True),
    )

    product_raw = raw["product"]
    product = ProductPluginConfig(
        plugin=product_raw["plugin"],
        short_name=product_raw["short_name"],
        version=product_raw.get("version"),
        variable_map=product_raw.get("variable_map", {}),
        preferred_output_bands=product_raw.get("preferred_output_bands", []),
        native_epsg=product_raw.get("native_epsg"),
        latitude_var=product_raw.get("latitude_var", "latitude"),
        longitude_var=product_raw.get("longitude_var", "longitude"),
        x_var=product_raw.get("x_var", "x"),
        y_var=product_raw.get("y_var", "y"),
        downloader_compatibility=product_raw.get("downloader_compatibility", []),
        ui_defaults=product_raw.get("ui_defaults", {}),
    )

    chunk_raw = raw.get("chunking", {})
    chunking = ChunkingConfig(
        enabled=chunk_raw.get("enabled", True),
        mode=chunk_raw.get("mode", "auto"),
        max_tile_area_km2=float(chunk_raw.get("max_tile_area_km2", 300_000.0)),
        max_tile_span_deg=float(chunk_raw.get("max_tile_span_deg", 8.0)),
        max_tiles=int(chunk_raw.get("max_tiles", 400)),
    )

    return PipelineConfig(
        date_range=date_range,
        aoi=aoi,
        data_access=data_access,
        process=process,
        publish=publish,
        auth=auth,
        product=product,
        chunking=chunking,
        run_label=raw.get("run_label"),
    )


def config_to_dict(config: PipelineConfig) -> dict[str, Any]:
    data = asdict(config)
    _stringify_paths(data)
    return data


def save_config(config: PipelineConfig, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = config_to_dict(config)
    out.write_text(yaml.safe_dump(payload, sort_keys=False))
    return out


def _stringify_paths(node: Any) -> Any:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, Path):
                node[key] = str(value)
            else:
                _stringify_paths(value)
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            if isinstance(value, Path):
                node[idx] = str(value)
            else:
                _stringify_paths(value)
    return node
