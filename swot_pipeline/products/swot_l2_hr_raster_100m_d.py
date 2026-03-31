from __future__ import annotations

from typing import Any

import numpy as np

from swot_pipeline.products.base import ProductPlugin


class SWOTL2HRRaster100mDPlugin(ProductPlugin):
    plugin_name = "swot_l2_hr_raster_100m_d"
    short_name = "SWOT_L2_HR_Raster_100m_D"

    required_variables = ["wse", "wse_qual", "wse_uncert", "water_frac", "n_wse_pix"]
    optional_variables = [
        "water_area",
        "water_area_qual",
        "water_area_uncert",
        "sig0",
        "sig0_qual",
        "sig0_uncert",
        "cross_track",
        "inc",
        "illumination_time",
        "bitwise_qa",
    ]

    def build_quality_masks(
        self,
        extracted: dict[str, np.ndarray],
        quality_rules: dict[str, Any],
    ) -> dict[str, np.ndarray]:
        wse_qual = extracted.get("wse_qual")
        water_frac = extracted.get("water_frac")
        n_wse_pix = extracted.get("n_wse_pix")
        wse_uncert = extracted.get("wse_uncert")

        if wse_qual is None:
            raise ValueError("wse_qual is required to generate QA masks")

        basic_max_qual = quality_rules.get("basic_max_wse_qual", 1)
        basic_min_water_frac = quality_rules.get("basic_min_water_frac", 0.05)
        basic_min_wse_pix = quality_rules.get("basic_min_n_wse_pix", 1)

        strict_max_qual = quality_rules.get("strict_max_wse_qual", 0)
        strict_min_water_frac = quality_rules.get("strict_min_water_frac", 0.2)
        strict_min_wse_pix = quality_rules.get("strict_min_n_wse_pix", 4)
        strict_max_wse_uncert = quality_rules.get("strict_max_wse_uncert", 0.5)

        basic = np.ones_like(wse_qual, dtype=np.uint8)
        strict = np.ones_like(wse_qual, dtype=np.uint8)

        basic &= (wse_qual <= basic_max_qual).astype(np.uint8)
        strict &= (wse_qual <= strict_max_qual).astype(np.uint8)

        if water_frac is not None:
            basic &= (water_frac >= basic_min_water_frac).astype(np.uint8)
            strict &= (water_frac >= strict_min_water_frac).astype(np.uint8)

        if n_wse_pix is not None:
            basic &= (n_wse_pix >= basic_min_wse_pix).astype(np.uint8)
            strict &= (n_wse_pix >= strict_min_wse_pix).astype(np.uint8)

        if wse_uncert is not None:
            strict &= (wse_uncert <= strict_max_wse_uncert).astype(np.uint8)

        # Optional product QA bands can tighten strict mask.
        water_area_qual = extracted.get("water_area_qual")
        sig0_qual = extracted.get("sig0_qual")
        if water_area_qual is not None:
            strict &= (water_area_qual <= quality_rules.get("strict_max_water_area_qual", 1)).astype(np.uint8)
        if sig0_qual is not None:
            strict &= (sig0_qual <= quality_rules.get("strict_max_sig0_qual", 1)).astype(np.uint8)

        return {
            "qa_keep_basic": basic,
            "qa_keep_strict": strict,
        }
