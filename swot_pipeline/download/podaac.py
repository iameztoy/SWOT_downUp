from __future__ import annotations

import shlex
import shutil
import time
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
        use_downloader_cli = bool(options.get("use_downloader_cli"))
        use_subscriber = bool(options.get("use_subscriber"))

        output_dir.mkdir(parents=True, exist_ok=True)
        before_files = self._list_candidate_files(output_dir)

        if use_subscriber:
            subscriber_extra = self._parse_extra_args(options.get("subscriber_cli_extra_args"))
            self._adapter.run_subscriber_cli_with_options(
                extra_args=subscriber_extra,
                timeout_s=self._as_int(options.get("subscriber_timeout_s"), default=90),
                timeout_is_ok=True,
            )

        if use_downloader_cli:
            downloader_extra = self._parse_extra_args(options.get("downloader_cli_extra_args"))
            self._adapter.run_downloader_cli_with_options(
                date_start=self.pipeline_config.date_range.start,
                date_end=self.pipeline_config.date_range.end,
                aoi=self.pipeline_config.aoi,
                output_dir=output_dir,
                extra_args=downloader_extra,
                timeout_s=self._as_int(options.get("downloader_timeout_s"), default=None),
            )
            return self._resolve_downloaded_granules(granules, output_dir)

        if use_subscriber:
            wait_timeout_s = self._as_int(options.get("subscriber_wait_timeout_s"), default=300) or 300
            poll_interval_s = self._as_int(options.get("subscriber_poll_interval_s"), default=10) or 10
            self._wait_for_new_files(output_dir, before_files, wait_timeout_s, poll_interval_s)
            return self._resolve_downloaded_granules(granules, output_dir)

        return self._adapter.download(granules, output_dir)

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        if not self.pipeline_config.data_access.short_name:
            errors.append("data_access.short_name is required")
        options = self.pipeline_config.data_access.downloader_options
        use_downloader_cli = bool(options.get("use_downloader_cli"))
        use_subscriber = bool(options.get("use_subscriber"))

        if use_downloader_cli and not self._is_command_available(self.pipeline_config.data_access.podaac_downloader_cmd):
            errors.append(
                "PO.DAAC downloader CLI not found. Install it and ensure "
                f"'{self.pipeline_config.data_access.podaac_downloader_cmd}' is on PATH "
                "(or set data_access.podaac_downloader_cmd to an absolute executable path)."
            )

        if use_subscriber and not self._is_command_available(self.pipeline_config.data_access.podaac_subscriber_cmd):
            errors.append(
                "PO.DAAC subscriber CLI not found. Install it and ensure "
                f"'{self.pipeline_config.data_access.podaac_subscriber_cmd}' is on PATH "
                "(or set data_access.podaac_subscriber_cmd to an absolute executable path)."
            )

        if use_subscriber and not use_downloader_cli:
            wait_timeout = self._as_int(options.get("subscriber_wait_timeout_s"), default=300) or 300
            if wait_timeout <= 0:
                errors.append("downloader_options.subscriber_wait_timeout_s must be > 0 for subscriber-only mode.")

        for key in ("subscriber_timeout_s", "subscriber_wait_timeout_s", "subscriber_poll_interval_s", "downloader_timeout_s"):
            value = options.get(key)
            if value is None:
                continue
            parsed = self._as_int(value, default=None)
            if parsed is None or parsed <= 0:
                errors.append(f"downloader_options.{key} must be a positive integer when provided.")

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
                "downloader_options.downloader_cli_extra_args",
                "downloader_options.subscriber_cli_extra_args",
                "downloader_options.subscriber_timeout_s",
                "downloader_options.subscriber_wait_timeout_s",
                "downloader_options.subscriber_poll_interval_s",
            ],
            "todo": "Add richer subscription state monitoring and replay-safe subscriber checkpoints.",
        }

    def _resolve_downloaded_granules(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        files = self._list_candidate_files(output_dir)
        by_name = {path.name: path for path in files}
        by_stem = {path.stem: path for path in files}

        resolved: list[GranuleRecord] = []
        for record in granules:
            match = by_name.get(record.filename)
            if not match:
                match = by_stem.get(Path(record.filename).stem)
            if not match:
                # Lenient fallback: match by granule_id fragment in filename.
                for candidate in files:
                    if record.granule_id and record.granule_id in candidate.name:
                        match = candidate
                        break
            if match:
                record.local_path = match
                resolved.append(record)

        if not resolved:
            raise RuntimeError(
                "PO.DAAC mode finished but no local files were matched to searched granules. "
                "Check downloader/subscriber command options and output directory."
            )
        return resolved

    def _wait_for_new_files(
        self,
        output_dir: Path,
        before_files: set[Path],
        wait_timeout_s: int,
        poll_interval_s: int,
    ) -> None:
        start = time.monotonic()
        while time.monotonic() - start < wait_timeout_s:
            now_files = self._list_candidate_files(output_dir)
            if any(path not in before_files for path in now_files):
                return
            time.sleep(max(poll_interval_s, 1))
        raise RuntimeError(
            "Subscriber mode timed out waiting for new files. "
            "Increase downloader_options.subscriber_wait_timeout_s or verify subscriber filters."
        )

    def _list_candidate_files(self, output_dir: Path) -> set[Path]:
        exts = {".nc", ".nc4", ".h5", ".hdf5", ".tif", ".tiff"}
        return {path for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in exts}

    def _parse_extra_args(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if str(v).strip()]
        if isinstance(value, str):
            if not value.strip():
                return []
            return shlex.split(value)
        return [str(value)]

    def _as_int(self, value: Any, default: int | None) -> int | None:
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _is_command_available(self, cmd: str | None) -> bool:
        if not cmd:
            return False
        if "/" in cmd:
            path = Path(cmd)
            return path.exists() and path.is_file()
        return shutil.which(cmd) is not None
