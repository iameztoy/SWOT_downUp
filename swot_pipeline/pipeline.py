from __future__ import annotations

from datetime import timezone
from pathlib import Path

import rasterio

from swot_pipeline.download import get_downloader
from swot_pipeline.models import GranuleRecord, PipelineConfig, ProcessedRaster, PublishResult
from swot_pipeline.processing.pipeline import process_granules
from swot_pipeline.products import get_product_plugin
from swot_pipeline.publish.ee_manifest import (
    build_asset_id,
    build_external_image_manifest,
    build_ingested_image_manifest,
    write_manifest,
)
from swot_pipeline.publish.ee_publisher import EarthEnginePublisher
from swot_pipeline.publish.gcs import stage_files_to_gcs
from swot_pipeline.utils.time import parse_datetime_from_filename


def search_granules(config: PipelineConfig, swodlr_cmd_template: str | None = None) -> list[GranuleRecord]:
    if swodlr_cmd_template:
        config.data_access.downloader_options["swodlr_cmd_template"] = swodlr_cmd_template
    downloader = get_downloader(config)
    return downloader.search(config.date_range.start, config.date_range.end, config.aoi)


def download_granules(
    config: PipelineConfig,
    granules: list[GranuleRecord],
    swodlr_cmd_template: str | None = None,
) -> list[GranuleRecord]:
    if swodlr_cmd_template:
        config.data_access.downloader_options["swodlr_cmd_template"] = swodlr_cmd_template
    downloader = get_downloader(config)
    return downloader.download(granules, config.data_access.output_dir)


def process_downloaded(config: PipelineConfig, granules: list[GranuleRecord]) -> list[ProcessedRaster]:
    plugin = get_product_plugin(config.product)
    return process_granules(granules, config=config, plugin=plugin)


def publish_processed(config: PipelineConfig, processed: list[ProcessedRaster]) -> list[PublishResult]:
    if not config.publish.enabled:
        return []

    gcs_map = stage_files_to_gcs(processed, config)
    publisher = EarthEnginePublisher(config.auth, config.publish)

    asset_root = config.publish.ee_asset_root or config.publish.ee_collection_root
    if not asset_root:
        raise ValueError("Set publish.ee_asset_root or publish.ee_collection_root in config")

    manifest_dir = Path("manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)

    results: list[PublishResult] = []
    for raster in processed:
        gcs_uri = gcs_map[raster.local_path]
        asset_id = build_asset_id(
            asset_root=asset_root,
            product_short_name=config.product.short_name,
            acquisition_time=raster.acquisition_time.astimezone(timezone.utc),
            granule_id=raster.source_granule.granule_id,
        )

        properties = {
            "product_short_name": config.product.short_name,
            "source_granule": raster.source_granule.granule_id,
            "processing_mode": raster.mode,
        }

        if config.publish.ee_mode == "external_image":
            manifest = build_external_image_manifest(
                asset_id=asset_id,
                cog_uri=gcs_uri,
                bands=raster.bands,
                acquisition_time=raster.acquisition_time,
                properties=properties,
            )
        else:
            manifest = build_ingested_image_manifest(
                asset_id=asset_id,
                gcs_uri=gcs_uri,
                bands=raster.bands,
                acquisition_time=raster.acquisition_time,
                properties=properties,
            )

        manifest_path = write_manifest(manifest_dir / f"{raster.local_path.stem}.manifest.json", manifest)
        result = publisher.publish_manifest(
            manifest=manifest,
            mode=config.publish.ee_mode,
            asset_id=asset_id,
            write_properties=config.publish.write_asset_properties,
        )
        result.details["manifest_path"] = str(manifest_path)
        results.append(result)

    return results


def run_pipeline(config: PipelineConfig, swodlr_cmd_template: str | None = None) -> tuple[
    list[GranuleRecord],
    list[GranuleRecord],
    list[ProcessedRaster],
    list[PublishResult],
]:
    found = search_granules(config, swodlr_cmd_template=swodlr_cmd_template)
    downloaded = download_granules(config, found, swodlr_cmd_template=swodlr_cmd_template)
    processed = process_downloaded(config, downloaded)
    published = publish_processed(config, processed)
    return found, downloaded, processed, published


def run_job_from_config(config: PipelineConfig, swodlr_cmd_template: str | None = None) -> tuple[
    list[GranuleRecord],
    list[GranuleRecord],
    list[ProcessedRaster],
    list[PublishResult],
]:
    found = search_granules(config, swodlr_cmd_template=swodlr_cmd_template)
    downloaded = download_granules(config, found, swodlr_cmd_template=swodlr_cmd_template)

    step = config.process.workflow_step.lower()
    if step == "raw_only":
        return found, downloaded, [], []

    processed = process_downloaded(config, downloaded)
    if step in {"extract", "qa"}:
        return found, downloaded, processed, []

    if config.publish.enabled and config.publish.publish_immediately:
        published = publish_processed(config, processed)
    else:
        published = []
    return found, downloaded, processed, published


def discover_local_granules(raw_dir: Path) -> list[GranuleRecord]:
    granules: list[GranuleRecord] = []
    for path in sorted(raw_dir.glob("*.nc")):
        granules.append(
            GranuleRecord(
                granule_id=path.stem,
                url="",
                filename=path.name,
                start_time=parse_datetime_from_filename(path.name),
                local_path=path,
            )
        )
    return granules


def discover_processed_rasters(processed_dir: Path) -> list[ProcessedRaster]:
    rasters: list[ProcessedRaster] = []
    for path in sorted(processed_dir.glob("*.tif")):
        with rasterio.open(path) as src:
            bands = [d for d in src.descriptions if d] or [f"band_{i}" for i in range(1, src.count + 1)]
            tags = src.tags()
        acquisition_time = parse_datetime_from_filename(path.name)
        if acquisition_time is None and "acquisition_time" in tags:
            from datetime import datetime

            acquisition_time = datetime.fromisoformat(tags["acquisition_time"].replace("Z", "+00:00"))
        if acquisition_time is None:
            raise ValueError(f"Could not infer acquisition time for {path}")

        granule = GranuleRecord(granule_id=path.stem, url="", filename=path.name)
        rasters.append(
            ProcessedRaster(
                source_granule=granule,
                local_path=path,
                bands=bands,
                acquisition_time=acquisition_time,
                mode=tags.get("output_mode", "ee_ready"),
                metadata=tags,
            )
        )
    return rasters
