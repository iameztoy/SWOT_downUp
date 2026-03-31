from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from swot_pipeline.adapters.base import DataAdapter
from swot_pipeline.adapters.cmr import cmr_search
from swot_pipeline.models import AOIConfig, AuthConfig, GranuleRecord
from swot_pipeline.utils.auth import build_earthdata_session


class HarmonyAdapter(DataAdapter):
    """Optional adapter for Harmony/SWODLR transformed GeoTIFF requests.

    Two execution paths are supported:
    1) direct download when CMR returns a GeoTIFF link,
    2) external SWODLR/Harmony command template when source is NetCDF.
    """

    def __init__(self, config, auth: AuthConfig | None = None, swodlr_cmd_template: str | None = None):
        super().__init__(config)
        self.auth = auth or AuthConfig()
        self.swodlr_cmd_template = swodlr_cmd_template

    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        records = cmr_search(self.config, date_start, date_end, aoi)
        return records

    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        output_dir.mkdir(parents=True, exist_ok=True)
        session = build_earthdata_session(self.auth)

        for record in granules:
            target_name = Path(record.filename).with_suffix(".tif").name
            target = output_dir / target_name

            if record.url.lower().endswith((".tif", ".tiff", ".cog.tif")):
                with session.get(record.url, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    with target.open("wb") as fp:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                fp.write(chunk)
            elif self.swodlr_cmd_template:
                cmd = self.swodlr_cmd_template.format(input_url=record.url, output_path=str(target))
                subprocess.run(cmd, shell=True, check=True)
            else:
                raise RuntimeError(
                    "Harmony adapter needs either GeoTIFF URLs from search or a swodlr_cmd_template in runtime."
                )

            record.local_path = target

        return granules
