from __future__ import annotations

from swot_pipeline.models import ProductPluginConfig
from swot_pipeline.products.base import ProductPlugin
from swot_pipeline.products.swot_l2_hr_raster_100m_d import SWOTL2HRRaster100mDPlugin

_PLUGIN_REGISTRY: dict[str, type[ProductPlugin]] = {
    SWOTL2HRRaster100mDPlugin.plugin_name: SWOTL2HRRaster100mDPlugin,
}


def get_product_plugin(config: ProductPluginConfig) -> ProductPlugin:
    if config.plugin not in _PLUGIN_REGISTRY:
        raise ValueError(
            f"Unknown product plugin '{config.plugin}'. Registered plugins: {sorted(_PLUGIN_REGISTRY)}"
        )
    return _PLUGIN_REGISTRY[config.plugin](config)


def list_product_plugins() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for plugin_name, cls in _PLUGIN_REGISTRY.items():
        default_cfg = ProductPluginConfig(plugin=plugin_name, short_name=cls.short_name)
        plugin = cls(default_cfg)
        items.append(plugin.get_metadata())
    return sorted(items, key=lambda x: str(x["short_name"]))
