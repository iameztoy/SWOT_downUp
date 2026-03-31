from __future__ import annotations

import copy
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from app.models.db import JobDatabase
from swot_pipeline.aoi import chunk_geometry, geometry_summary, parse_aoi_payload
from swot_pipeline.config import parse_config_dict, save_config
from swot_pipeline.download import get_downloader
from swot_pipeline.models import AOIConfig, PipelineConfig
from swot_pipeline.pipeline import download_granules, process_downloaded, publish_processed, search_granules


class JobCanceledError(Exception):
    pass


class JobRunner:
    def __init__(self, db: JobDatabase, max_workers: int = 2):
        self.db = db
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="swot-job")

    def submit(self, job_id: str, config_json: dict[str, Any]) -> None:
        self.pool.submit(self._run_job, job_id, config_json)

    def _run_job(self, job_id: str, config_json: dict[str, Any]) -> None:
        try:
            self.db.update_job(job_id, status="validating", message="Validating configuration", progress=0.02)
            self._raise_if_canceled(job_id)
            config = parse_config_dict(config_json)
            self._validate_downloader(config)

            aoi_payload = self._aoi_payload_from_config(config)
            geom = parse_aoi_payload(aoi_payload)
            aoi_summary = geometry_summary(geom)

            self.db.add_log(job_id, "INFO", "AOI validated", aoi_summary)
            self.db.update_job(
                job_id,
                status="queued",
                message=f"AOI size: {aoi_summary['size_class']} ({aoi_summary['area_km2']:.1f} km2)",
                progress=0.05,
            )

            chunks = self._build_chunks(config, geom, aoi_summary)
            self.db.add_log(job_id, "INFO", "Chunk plan computed", {"chunk_count": len(chunks)})

            snapshot_dir = Path("data/jobs") / job_id
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = snapshot_dir / "config.snapshot.yaml"
            save_config(config, snapshot_path)
            self.db.add_output(job_id, "config_snapshot", str(snapshot_path), {"format": "yaml"})

            total_chunks = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                self._raise_if_canceled(job_id)
                chunk_progress_base = 0.05 + ((idx - 1) / max(total_chunks, 1)) * 0.9
                self.db.update_job(
                    job_id,
                    status="running",
                    message=f"Running chunk {idx}/{total_chunks}: {chunk['label']}",
                    progress=chunk_progress_base,
                )
                self._run_chunk(job_id, config, chunk)

                self.db.update_job(job_id, progress=0.05 + (idx / max(total_chunks, 1)) * 0.9)

            self._raise_if_canceled(job_id)
            self.db.update_job(job_id, status="completed", message="Job completed", progress=1.0)
            self.db.add_log(job_id, "INFO", "Job completed")
        except JobCanceledError:
            self.db.update_job(job_id, status="canceled", message="Job canceled by user")
            self.db.add_log(job_id, "WARNING", "Job canceled")
        except Exception as exc:
            self.db.update_job(job_id, status="failed", error=str(exc), message="Job failed")
            self.db.add_log(job_id, "ERROR", "Job failed", {"error": str(exc), "traceback": traceback.format_exc()})

    def _run_chunk(self, job_id: str, base_config: PipelineConfig, chunk: dict[str, Any]) -> None:
        chunk_config = copy.deepcopy(base_config)
        chunk_label = chunk["label"]
        chunk_bbox = tuple(chunk["bbox"])

        chunk_config.aoi = AOIConfig(bbox=chunk_bbox, method="bbox")

        # Keep outputs stable and resumable by chunk folder.
        chunk_root = Path("data/jobs") / job_id / "chunks" / chunk_label
        raw_dir = chunk_root / "raw"
        processed_dir = chunk_root / "processed"
        marker = chunk_root / ".done"

        chunk_config.data_access.output_dir = raw_dir
        chunk_config.process.output_dir = processed_dir
        if chunk_config.publish.gcs_prefix:
            chunk_config.publish.gcs_prefix = f"{chunk_config.publish.gcs_prefix.rstrip('/')}/{chunk_label}"

        if marker.exists():
            self.db.add_log(job_id, "INFO", f"Skipping completed chunk {chunk_label}")
            return

        chunk_root.mkdir(parents=True, exist_ok=True)
        self._raise_if_canceled(job_id)
        self.db.add_log(job_id, "INFO", f"Starting chunk {chunk_label}", {"bbox": chunk_bbox})

        found = search_granules(chunk_config)
        self._raise_if_canceled(job_id)
        self.db.add_log(job_id, "INFO", f"Chunk {chunk_label}: found {len(found)} granules")

        downloaded = download_granules(chunk_config, found)
        self._raise_if_canceled(job_id)
        self.db.add_log(job_id, "INFO", f"Chunk {chunk_label}: downloaded {len(downloaded)} granules")

        for granule in downloaded:
            if granule.local_path:
                self.db.add_output(job_id, "raw_file", str(granule.local_path), {"chunk": chunk_label})

        workflow_step = chunk_config.process.workflow_step.lower()
        if workflow_step == "raw_only":
            marker.write_text("done")
            return

        processed = process_downloaded(chunk_config, downloaded)
        self._raise_if_canceled(job_id)
        self.db.add_log(job_id, "INFO", f"Chunk {chunk_label}: processed {len(processed)} outputs")
        for raster in processed:
            self.db.add_output(job_id, "processed_raster", str(raster.local_path), {"chunk": chunk_label})

        if workflow_step in {"extract", "qa"}:
            marker.write_text("done")
            return

        if chunk_config.publish.enabled and chunk_config.publish.publish_immediately:
            published = publish_processed(chunk_config, processed)
            self._raise_if_canceled(job_id)
            self.db.add_log(job_id, "INFO", f"Chunk {chunk_label}: published {len(published)} assets")
            for item in published:
                self.db.add_output(
                    job_id,
                    "published_asset",
                    item.asset_id,
                    {"task_id": item.task_id, "state": item.state, "chunk": chunk_label},
                )

        marker.write_text("done")

    def _validate_downloader(self, config: PipelineConfig) -> None:
        downloader = get_downloader(config)
        errors = downloader.validate_config()
        if errors:
            raise ValueError("; ".join(errors))

    def _build_chunks(self, config: PipelineConfig, geom, summary: dict[str, Any]) -> list[dict[str, Any]]:
        mode = config.chunking.mode.lower()
        size_class = summary["size_class"]

        should_chunk = config.chunking.enabled
        if mode == "never":
            should_chunk = False
        elif mode == "always":
            should_chunk = True
        elif mode == "auto":
            should_chunk = size_class == "large"

        if not should_chunk:
            return [{"label": "tile_000_000", "bbox": list(geom.bounds), "area_km2": summary["area_km2"]}]

        chunks = chunk_geometry(
            geom=geom,
            max_tile_area_km2=config.chunking.max_tile_area_km2,
            max_tile_span_deg=config.chunking.max_tile_span_deg,
            max_tiles=config.chunking.max_tiles,
        )
        if not chunks:
            return [{"label": "tile_000_000", "bbox": list(geom.bounds), "area_km2": summary["area_km2"]}]

        return [
            {
                "label": chunk.label,
                "bbox": list(chunk.bbox),
                "area_km2": chunk.area_km2,
            }
            for chunk in chunks
        ]

    def _aoi_payload_from_config(self, config: PipelineConfig) -> dict[str, Any]:
        method = config.aoi.method or "bbox"
        payload: dict[str, Any] = {"method": method}
        if config.aoi.bbox:
            payload["bbox"] = list(config.aoi.bbox)
        if config.aoi.polygon_wkt:
            payload["wkt"] = config.aoi.polygon_wkt
        if config.aoi.geojson:
            payload["geojson"] = config.aoi.geojson
        if config.aoi.preset_id:
            payload["preset_id"] = config.aoi.preset_id
        if config.aoi.polygon_path:
            if config.aoi.polygon_path.suffix.lower() == ".zip":
                payload = {"method": "shapefile_zip", "zip_path": str(config.aoi.polygon_path)}
            else:
                # Parse local GeoJSON-like files as geojson payload.
                payload = {"method": "geojson", "geojson": yaml.safe_load(config.aoi.polygon_path.read_text())}
        return payload

    def _raise_if_canceled(self, job_id: str) -> None:
        record = self.db.get_job(job_id)
        if record and record.get("status") == "canceled":
            raise JobCanceledError(job_id)
