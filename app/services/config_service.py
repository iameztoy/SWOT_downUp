from __future__ import annotations

from typing import Any

import yaml

from swot_pipeline.config import config_to_dict, parse_config_dict


def preview_config(config_dict: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_config_dict(config_dict)
    normalized = config_to_dict(parsed)
    yaml_text = yaml.safe_dump(normalized, sort_keys=False)

    warnings: list[str] = []
    if parsed.publish.enabled and not parsed.publish.gcs_bucket:
        warnings.append("Publish is enabled but publish.gcs_bucket is empty")
    if parsed.chunking.enabled and parsed.chunking.mode == "auto":
        warnings.append("Chunking mode is auto: large AOIs will be tiled automatically")

    return {
        "normalized_config": normalized,
        "yaml": yaml_text,
        "warnings": warnings,
    }
