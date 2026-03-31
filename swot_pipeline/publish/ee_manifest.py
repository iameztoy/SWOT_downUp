from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from swot_pipeline.utils.time import to_epoch_millis, to_rfc3339


_SAFE = re.compile(r"[^A-Za-z0-9_\-]")


def sanitize_asset_component(value: str) -> str:
    return _SAFE.sub("_", value)


def build_asset_id(asset_root: str, product_short_name: str, acquisition_time: datetime, granule_id: str) -> str:
    ts = acquisition_time.strftime("%Y/%m/%d")
    granule_slug = sanitize_asset_component(granule_id)
    product_slug = sanitize_asset_component(product_short_name)
    return f"{asset_root.rstrip('/')}/{product_slug}/{ts}/{granule_slug}"


def build_ingested_image_manifest(
    asset_id: str,
    gcs_uri: str,
    bands: list[str],
    acquisition_time: datetime,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    props = dict(properties or {})
    props.setdefault("system:time_start", to_epoch_millis(acquisition_time))

    return {
        "name": _to_ee_asset_name(asset_id),
        "tilesets": [{"id": "ts1", "sources": [{"uris": [gcs_uri]}]}],
        "bands": [
            {"id": band, "tileset_id": "ts1", "tileset_band_index": idx}
            for idx, band in enumerate(bands)
        ],
        "start_time": to_rfc3339(acquisition_time),
        "properties": props,
    }


def build_external_image_manifest(
    asset_id: str,
    cog_uri: str,
    bands: list[str],
    acquisition_time: datetime,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    props = dict(properties or {})
    props.setdefault("system:time_start", to_epoch_millis(acquisition_time))

    return {
        "name": _to_ee_asset_name(asset_id),
        "tilesets": [{"id": "ts1", "sources": [{"uris": [cog_uri]}]}],
        "bands": [{"id": band} for band in bands],
        "start_time": to_rfc3339(acquisition_time),
        "properties": props,
    }


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    return out


def _to_ee_asset_name(asset_id: str) -> str:
    if asset_id.startswith("projects/"):
        return asset_id
    return f"projects/earthengine-legacy/assets/{asset_id}"
