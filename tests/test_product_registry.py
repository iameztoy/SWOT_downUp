from swot_pipeline.products import list_product_plugins


def test_product_registry_contains_swot_karin_100m():
    products = list_product_plugins()
    names = {p["plugin"] for p in products}
    assert "swot_l2_hr_raster_100m_d" in names

    swot = next(p for p in products if p["plugin"] == "swot_l2_hr_raster_100m_d")
    assert "wse" in swot["required_variables"]
