from __future__ import annotations

from swot_pipeline.products import list_product_plugins


def get_products() -> list[dict[str, object]]:
    return list_product_plugins()
