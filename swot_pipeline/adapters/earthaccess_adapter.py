from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from swot_pipeline.adapters.base import DataAdapter
from swot_pipeline.models import AOIConfig, AuthConfig, GranuleRecord
from swot_pipeline.utils.auth import resolve_earthdata_credentials


class EarthaccessAdapter(DataAdapter):
    def __init__(self, config, auth: AuthConfig | None = None):
        super().__init__(config)
        self.auth = auth or AuthConfig()

    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        try:
            import earthaccess
        except ImportError as exc:
            raise RuntimeError("earthaccess mode requires `pip install earthaccess`") from exc

        self._login(earthaccess)

        bbox = tuple(aoi.bbox) if aoi.bbox else None
        results = earthaccess.search_data(
            short_name=self.config.short_name,
            version=self.config.version,
            temporal=(date_start.isoformat(), date_end.isoformat()),
            bounding_box=bbox,
            provider=self.config.provider,
            count=self.config.max_results,
        )

        records: list[GranuleRecord] = []
        for result in results:
            links = []
            if hasattr(result, "data_links"):
                links = result.data_links(access="direct") or result.data_links() or []
            if not links:
                continue

            url = links[0]
            title = result.umm.get("GranuleUR") if hasattr(result, "umm") else Path(url).name
            temporal = result.umm.get("TemporalExtent", {}).get("RangeDateTime", {}) if hasattr(result, "umm") else {}

            records.append(
                GranuleRecord(
                    granule_id=title,
                    url=url,
                    filename=Path(url).name,
                    start_time=_parse_time(temporal.get("BeginningDateTime")),
                    end_time=_parse_time(temporal.get("EndingDateTime")),
                    metadata={"earthaccess_granule": result},
                )
            )

        return records

    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        try:
            import earthaccess
        except ImportError as exc:
            raise RuntimeError("earthaccess mode requires `pip install earthaccess`") from exc

        self._login(earthaccess)
        output_dir.mkdir(parents=True, exist_ok=True)

        raw_granules = [g.metadata.get("earthaccess_granule") for g in granules if g.metadata.get("earthaccess_granule")]
        if raw_granules:
            earthaccess.download(raw_granules, local_path=str(output_dir))
        else:
            # Fallback: direct HTTP download if records were reconstructed from cache.
            import requests

            for record in granules:
                target = output_dir / record.filename
                with requests.get(record.url, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    with target.open("wb") as fp:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                fp.write(chunk)
                record.local_path = target

        for record in granules:
            target = output_dir / record.filename
            if target.exists():
                record.local_path = target

        return granules

    def _login(self, earthaccess_module) -> None:
        user, password = resolve_earthdata_credentials(self.auth)
        if user and password:
            os.environ["EARTHDATA_USERNAME"] = user
            os.environ["EARTHDATA_PASSWORD"] = password
            earthaccess_module.login(strategy="environment", persist=False)
            return

        # If creds are missing from config/env, earthaccess can still use .netrc or existing session.
        earthaccess_module.login(strategy="netrc", persist=False)


def _parse_time(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
