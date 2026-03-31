import numpy as np
import xarray as xr

from swot_pipeline.models import AOIConfig, ProductPluginConfig
from swot_pipeline.processing.extract import extract_variables
from swot_pipeline.products.swot_l2_hr_raster_100m_d import SWOTL2HRRaster100mDPlugin


def test_extract_variables_with_bbox_mask():
    lat = np.array([40.0, 41.0])
    lon = np.array([1.0, 2.0, 3.0])
    wse = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    wse_qual = np.array([[0, 1, 2], [0, 0, 0]], dtype=np.uint8)
    wse_uncert = np.ones_like(wse)
    water_frac = np.full_like(wse, 0.7)
    n_wse_pix = np.full_like(wse, 5)

    ds = xr.Dataset(
        data_vars={
            "wse": (("y", "x"), wse),
            "wse_qual": (("y", "x"), wse_qual),
            "wse_uncert": (("y", "x"), wse_uncert),
            "water_frac": (("y", "x"), water_frac),
            "n_wse_pix": (("y", "x"), n_wse_pix),
        },
        coords={
            "latitude": ("y", lat),
            "longitude": ("x", lon),
        },
    )

    plugin = SWOTL2HRRaster100mDPlugin(
        ProductPluginConfig(plugin="swot_l2_hr_raster_100m_d", short_name="SWOT_L2_HR_Raster_100m_D")
    )

    out = extract_variables(
        ds,
        plugin,
        requested_bands=["wse", "wse_qual", "wse_uncert", "water_frac", "n_wse_pix"],
        aoi=AOIConfig(bbox=(0.5, 40.5, 2.5, 41.5)),
    )

    assert out["wse"].shape == (2, 3)
    # lon=3 is outside bbox and should be masked to nan for float arrays.
    assert np.isnan(out["wse"][0, 2])
    # Integer arrays are masked to 0.
    assert out["wse_qual"][0, 2] == 0
