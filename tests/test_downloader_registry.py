from swot_pipeline.config import parse_config_dict
from swot_pipeline.download import get_downloader, list_downloaders


def _minimal_config(mode: str):
    return parse_config_dict(
        {
            "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
            "aoi": {"bbox": [-1, 40, 1, 41], "method": "bbox"},
            "data_access": {"mode": mode, "short_name": "SWOT_L2_HR_Raster_100m_D"},
            "process": {"variables": ["wse", "wse_qual", "wse_uncert", "water_frac", "n_wse_pix"]},
            "publish": {"enabled": False},
            "auth": {},
            "product": {"plugin": "swot_l2_hr_raster_100m_d", "short_name": "SWOT_L2_HR_Raster_100m_D"},
        }
    )


def test_downloader_registry_lists_expected_modes():
    modes = {d["name"] for d in list_downloaders()}
    assert {"earthaccess", "podaac", "harmony"}.issubset(modes)


def test_get_downloader_returns_adapter_with_capabilities():
    cfg = _minimal_config("podaac")
    downloader = get_downloader(cfg)
    caps = downloader.get_capabilities()
    assert caps["supports_search"] is True
