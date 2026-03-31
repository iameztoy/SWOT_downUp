from pathlib import Path

from swot_pipeline.config import load_config


def test_load_config(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
date_range:
  start: "2024-01-01T00:00:00Z"
  end: "2024-01-02T00:00:00Z"
aoi:
  bbox: [0, 1, 2, 3]
data_access:
  mode: "earthaccess"
  short_name: "SWOT_L2_HR_Raster_100m_D"
process:
  variables: [wse, wse_qual, wse_uncert, water_frac, n_wse_pix]
publish:
  enabled: false
auth: {}
product:
  plugin: "swot_l2_hr_raster_100m_d"
  short_name: "SWOT_L2_HR_Raster_100m_D"
"""
    )

    loaded = load_config(cfg)

    assert loaded.data_access.mode == "earthaccess"
    assert loaded.aoi.bbox == (0, 1, 2, 3)
    assert loaded.process.variables[0] == "wse"
    assert loaded.product.plugin == "swot_l2_hr_raster_100m_d"
