from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Sequence

from swot_pipeline.adapters.base import DataAdapter
from swot_pipeline.adapters.cmr import cmr_search
from swot_pipeline.models import AOIConfig, AuthConfig, GranuleRecord
from swot_pipeline.utils.auth import build_earthdata_session


class PODAACAdapter(DataAdapter):
    """PO.DAAC integration with CMR search + authenticated download.

    This adapter can also trigger external PO.DAAC tools when available.
    """

    def __init__(self, config, auth: AuthConfig | None = None):
        super().__init__(config)
        self.auth = auth or AuthConfig()

    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        return cmr_search(self.config, date_start, date_end, aoi)

    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        output_dir.mkdir(parents=True, exist_ok=True)
        session = build_earthdata_session(self.auth)

        for record in granules:
            target = output_dir / record.filename
            with session.get(record.url, stream=True, timeout=120) as response:
                response.raise_for_status()
                with target.open("wb") as fp:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            fp.write(chunk)
            record.local_path = target

        return granules

    def run_downloader_cli(self, date_start: datetime, date_end: datetime, aoi: AOIConfig, output_dir: Path) -> None:
        self.run_downloader_cli_with_options(
            date_start=date_start,
            date_end=date_end,
            aoi=aoi,
            output_dir=output_dir,
            extra_args=[],
            timeout_s=None,
        )

    def run_downloader_cli_with_options(
        self,
        date_start: datetime,
        date_end: datetime,
        aoi: AOIConfig,
        output_dir: Path,
        extra_args: Sequence[str] | None = None,
        timeout_s: int | None = None,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.config.podaac_downloader_cmd,
            "-c",
            self.config.short_name,
            "-d",
            str(output_dir),
            "--start-date",
            date_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--end-date",
            date_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ]
        if aoi.bbox:
            cmd.extend(["--bbox", ",".join(str(v) for v in aoi.bbox)])
        if extra_args:
            cmd.extend(extra_args)
        subprocess.run(cmd, check=True, timeout=timeout_s)

    def run_subscriber_cli(self) -> None:
        self.run_subscriber_cli_with_options(extra_args=[], timeout_s=None, timeout_is_ok=False)

    def run_subscriber_cli_with_options(
        self,
        extra_args: Sequence[str] | None = None,
        timeout_s: int | None = None,
        timeout_is_ok: bool = True,
    ) -> None:
        cmd = [
            self.config.podaac_subscriber_cmd,
            "-c",
            self.config.short_name,
        ]
        if extra_args:
            cmd.extend(extra_args)
        try:
            subprocess.run(cmd, check=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            if not timeout_is_ok:
                raise
