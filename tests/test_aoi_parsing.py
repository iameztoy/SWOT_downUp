from swot_pipeline.aoi import geometry_summary, parse_aoi_payload


def test_parse_bbox_payload():
    geom = parse_aoi_payload({"method": "bbox", "bbox": [-5, 40, 5, 45]})
    summary = geometry_summary(geom)
    assert summary["bbox"][0] == -5
    assert summary["bbox"][2] == 5
    assert summary["area_km2"] > 0


def test_parse_wkt_payload():
    geom = parse_aoi_payload(
        {
            "method": "wkt",
            "wkt": "POLYGON((-5 40, 5 40, 5 45, -5 45, -5 40))",
        }
    )
    summary = geometry_summary(geom)
    assert summary["is_valid"] is True
