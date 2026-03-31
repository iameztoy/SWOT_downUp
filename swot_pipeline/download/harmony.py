from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from swot_pipeline.adapters.harmony_adapter import HarmonyAdapter
from swot_pipeline.download.base import DownloaderAdapter
from swot_pipeline.models import AOIConfig, GranuleRecord


class HarmonyDownloader(DownloaderAdapter):
    """Scaffold adapter for Harmony/SWODLR transformed-output workflows.

    TODO(next): add robust Harmony job orchestration and transformed asset polling.
    """
    name = "harmony"
    display_name = "SWODLR/Harmony (Transformed)"

    def __init__(self, pipeline_config):
        super().__init__(pipeline_config)
        options = pipeline_config.data_access.downloader_options
        self._adapter = HarmonyAdapter(
            pipeline_config.data_access,
            auth=pipeline_config.auth,
            swodlr_cmd_template=options.get("swodlr_cmd_template"),
        )

    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        return self._adapter.search(date_start, date_end, aoi)

    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        return self._adapter.download(granules, output_dir)

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        options = self.pipeline_config.data_access.downloader_options
        has_template = bool(options.get("swodlr_cmd_template"))
        if not has_template:
            errors.append(
                "Harmony mode expects downloader_options.swodlr_cmd_template unless CMR returns GeoTIFF links"
            )
        return errors

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "implementation_status": "scaffolded",
            "supports_search": True,
            "supports_direct_download": True,
            "supports_subscription": False,
            "supports_transformed_output": True,
            "ui_fields": [
                "downloader_options.swodlr_cmd_template",
                "downloader_options.output_format",
                "downloader_options.reprojection",
                "downloader_options.subset",
            ],
            "todo": "Complete server-side Harmony transformation request lifecycle.",
        }
