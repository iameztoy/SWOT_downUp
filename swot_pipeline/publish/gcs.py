from __future__ import annotations

import subprocess
from pathlib import Path

from swot_pipeline.models import PipelineConfig, ProcessedRaster
from swot_pipeline.utils.auth import configure_gcp_credentials


def stage_files_to_gcs(processed: list[ProcessedRaster], config: PipelineConfig) -> dict[Path, str]:
    if not config.publish.gcs_bucket:
        raise ValueError("publish.gcs_bucket is required for staging")

    configure_gcp_credentials(config.auth)
    mapping: dict[Path, str] = {}

    try:
        from google.cloud import storage  # type: ignore

        client = storage.Client(project=config.publish.project_id)
        bucket = client.bucket(config.publish.gcs_bucket)
        for raster in processed:
            blob_name = f"{config.publish.gcs_prefix.rstrip('/')}/{raster.local_path.name}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(raster.local_path))
            mapping[raster.local_path] = f"gs://{config.publish.gcs_bucket}/{blob_name}"
    except ImportError:
        for raster in processed:
            uri = f"gs://{config.publish.gcs_bucket}/{config.publish.gcs_prefix.rstrip('/')}/{raster.local_path.name}"
            subprocess.run(["gsutil", "cp", str(raster.local_path), uri], check=True)
            mapping[raster.local_path] = uri

    return mapping
