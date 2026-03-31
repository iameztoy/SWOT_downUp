from __future__ import annotations

from swot_pipeline.adapters.base import DataAdapter
from swot_pipeline.adapters.earthaccess_adapter import EarthaccessAdapter
from swot_pipeline.adapters.harmony_adapter import HarmonyAdapter
from swot_pipeline.adapters.podaac_adapter import PODAACAdapter
from swot_pipeline.models import AuthConfig, DataAccessConfig


def get_data_adapter(
    config: DataAccessConfig,
    auth: AuthConfig,
    swodlr_cmd_template: str | None = None,
) -> DataAdapter:
    mode = config.mode.lower()
    if mode == "earthaccess":
        return EarthaccessAdapter(config, auth=auth)
    if mode == "podaac":
        return PODAACAdapter(config, auth=auth)
    if mode in {"harmony", "swodlr"}:
        return HarmonyAdapter(config, auth=auth, swodlr_cmd_template=swodlr_cmd_template)

    raise ValueError(f"Unsupported data_access.mode={config.mode}. Use earthaccess, podaac, harmony, or swodlr")
