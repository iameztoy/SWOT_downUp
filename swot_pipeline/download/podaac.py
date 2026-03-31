from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from swot_pipeline.adapters.podaac_adapter import PODAACAdapter
from swot_pipeline.download.base import DownloaderAdapter
from swot_pipeline.models import AOIConfig, GranuleRecord


class PODAACDownloader(DownloaderAdapter):
    """Scaffold adapter for PO.DAAC downloader/subscriber integration.

    TODO(next): add robust subscription polling and end-to-end acceptance tests.
    """
    name = "podaac"
    display_name = "PO.DAAC Downloader/Subscriber"

    def __init__(self, pipeline_config):
        super().__init__(pipeline_config)
        self._adapter = PODAACAdapter(pipeline_config.data_access, auth=pipeline_config.auth)

    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        return self._adapter.search(date_start, date_end, aoi)

    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        options = self.pipeline_config.data_access.downloader_options
        if options.get("use_downloader_cli"):
            self._adapter.run_downloader_cli(date_start=self.pipeline_config.date_range.start,
                                             date_end=self.pipeline_config.date_range.end,
                                             aoi=self.pipeline_config.aoi,
                                             output_dir=output_dir)
            # Rehydrate local paths after CLI download.
            for record in granules:
                candidate = output_dir / record.filename
                if candidate.exists():
                    record.local_path = candidate
            return granules
        return self._adapter.download(granules, output_dir)

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        if not self.pipeline_config.data_access.short_name:
            errors.append("data_access.short_name is required")
        options = self.pipeline_config.data_access.downloader_options
        if options.get("use_subscriber") and not options.get("use_downloader_cli"):
            errors.append("Subscriber-only mode is scaffolded. Enable use_downloader_cli for now.")
        return errors

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "implementation_status": "scaffolded",
            "supports_search": True,
            "supports_direct_download": True,
            "supports_subscription": True,
            "supports_transformed_output": False,
            "ui_fields": [
                "podaac_downloader_cmd",
                "podaac_subscriber_cmd",
                "downloader_options.use_downloader_cli",
                "downloader_options.use_subscriber",
            ],
            "todo": "Complete subscriber auto-trigger and monitoring flow.",
        }
