import numpy as np

from swot_pipeline.models import ProductPluginConfig
from swot_pipeline.products.swot_l2_hr_raster_100m_d import SWOTL2HRRaster100mDPlugin


def test_qa_masks_basic_and_strict():
    plugin = SWOTL2HRRaster100mDPlugin(
        ProductPluginConfig(plugin="swot_l2_hr_raster_100m_d", short_name="SWOT_L2_HR_Raster_100m_D")
    )

    extracted = {
        "wse_qual": np.array([[0, 1, 2]]),
        "water_frac": np.array([[0.8, 0.1, 0.8]]),
        "n_wse_pix": np.array([[5, 5, 1]]),
        "wse_uncert": np.array([[0.1, 0.1, 0.9]]),
    }

    masks = plugin.build_quality_masks(extracted, quality_rules={})

    assert masks["qa_keep_basic"].tolist() == [[1, 1, 0]]
    assert masks["qa_keep_strict"].tolist() == [[1, 0, 0]]
