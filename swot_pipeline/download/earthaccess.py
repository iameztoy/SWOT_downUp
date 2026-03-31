from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from swot_pipeline.adapters.earthaccess_adapter import EarthaccessAdapter
from swot_pipeline.download.base import DownloaderAdapter
from swot_pipeline.models import AOIConfig, GranuleRecord


class EarthaccessDownloader(DownloaderAdapter):
    """Reference downloader path (fully implemented for vertical-slice smoke tests)."""
    name = "earthaccess"
    display_name = "Earthaccess"

    def __init__(self, pipeline_config):
        super().__init__(pipeline_config)
        self._adapter = EarthaccessAdapter(pipeline_config.data_access, auth=pipeline_config.auth)

    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        return self._adapter.search(date_start, date_end, aoi)

    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        return self._adapter.download(granules, output_dir)

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        if not self.pipeline_config.data_access.short_name:
            errors.append("data_access.short_name is required")
        return errors

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "implementation_status": "reference_ready",
            "supports_search": True,
            "supports_direct_download": True,
            "supports_subscription": False,
            "supports_transformed_output": False,
            "ui_fields": ["earthdata_username", "earthdata_password", "netrc_path"],
        }
