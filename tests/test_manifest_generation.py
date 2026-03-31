from datetime import datetime, timezone

from swot_pipeline.publish.ee_manifest import (
    build_asset_id,
    build_external_image_manifest,
    build_ingested_image_manifest,
)


def test_build_asset_id():
    dt = datetime(2024, 6, 1, tzinfo=timezone.utc)
    asset_id = build_asset_id(
        asset_root="users/me/swot",
        product_short_name="SWOT_L2_HR_Raster_100m_D",
        acquisition_time=dt,
        granule_id="granule:ABC",
    )
    assert asset_id.startswith("users/me/swot/SWOT_L2_HR_Raster_100m_D/2024/06/01/")
    assert "granule_ABC" in asset_id


def test_ingested_manifest_contains_time_start_and_bands():
    dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    manifest = build_ingested_image_manifest(
        asset_id="users/me/swot/a",
        gcs_uri="gs://bucket/file.tif",
        bands=["wse", "wse_qual"],
        acquisition_time=dt,
    )
    assert manifest["properties"]["system:time_start"] == int(dt.timestamp() * 1000)
    assert len(manifest["bands"]) == 2


def test_external_manifest_contains_tileset_source():
    dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    manifest = build_external_image_manifest(
        asset_id="users/me/swot/b",
        cog_uri="gs://bucket/file.tif",
        bands=["wse"],
        acquisition_time=dt,
    )
    assert manifest["tilesets"][0]["sources"][0]["uris"][0] == "gs://bucket/file.tif"
