from __future__ import annotations

from typing import Any

from swot_pipeline.download.base import DownloaderAdapter
from swot_pipeline.download.earthaccess import EarthaccessDownloader
from swot_pipeline.download.harmony import HarmonyDownloader
from swot_pipeline.download.podaac import PODAACDownloader
from swot_pipeline.models import PipelineConfig

_DOWNLOADER_REGISTRY: dict[str, type[DownloaderAdapter]] = {
    EarthaccessDownloader.name: EarthaccessDownloader,
    PODAACDownloader.name: PODAACDownloader,
    HarmonyDownloader.name: HarmonyDownloader,
    "swodlr": HarmonyDownloader,
}


def get_downloader(config: PipelineConfig) -> DownloaderAdapter:
    mode = config.data_access.mode.lower()
    if mode not in _DOWNLOADER_REGISTRY:
        raise ValueError(f"Unknown downloader mode '{config.data_access.mode}'. Available: {sorted(set(_DOWNLOADER_REGISTRY))}")
    return _DOWNLOADER_REGISTRY[mode](config)


def list_downloaders() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name, cls in _DOWNLOADER_REGISTRY.items():
        canonical = cls.name
        if canonical in seen:
            continue
        seen.add(canonical)
        # We expose static metadata without requiring a full pipeline config instance.
        items.append(
            {
                "name": canonical,
                "display_name": cls.display_name,
                "description": {
                    "earthaccess": "Earthaccess search + authenticated download via Earthdata Login",
                    "podaac": "CMR search + PO.DAAC downloader/subscriber integration",
                    "harmony": "Harmony/SWODLR transformed-output mode (GeoTIFF-ready workflows)",
                }.get(canonical, canonical),
                "implementation_status": {
                    "earthaccess": "reference_ready",
                    "podaac": "scaffolded",
                    "harmony": "scaffolded",
                }.get(canonical, "scaffolded"),
                "capabilities": {
                    "supports_search": True,
                    "supports_direct_download": True,
                    "supports_subscription": canonical == "podaac",
                    "supports_transformed_output": canonical == "harmony",
                },
                "ui_fields": {
                    "earthaccess": ["earthdata_username", "earthdata_password", "netrc_path"],
                    "podaac": [
                        "podaac_downloader_cmd",
                        "podaac_subscriber_cmd",
                        "downloader_options.use_downloader_cli",
                        "downloader_options.use_subscriber",
                    ],
                    "harmony": [
                        "downloader_options.swodlr_cmd_template",
                        "downloader_options.output_format",
                        "downloader_options.reprojection",
                        "downloader_options.subset",
                    ],
                }.get(canonical, []),
            }
        )
    return sorted(items, key=lambda x: x["name"])
