from swot_pipeline.config import parse_config_dict
from swot_pipeline.download import get_downloader


def _cfg(mode: str, downloader_options: dict | None = None):
    return parse_config_dict(
        {
            "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
            "aoi": {"bbox": [-1, 40, 1, 41], "method": "bbox"},
            "data_access": {
                "mode": mode,
                "short_name": "SWOT_L2_HR_Raster_100m_D",
                "downloader_options": downloader_options or {},
            },
            "process": {"variables": ["wse", "wse_qual", "wse_uncert", "water_frac", "n_wse_pix"]},
            "publish": {"enabled": False},
            "auth": {},
            "product": {"plugin": "swot_l2_hr_raster_100m_d", "short_name": "SWOT_L2_HR_Raster_100m_D"},
        }
    )


def test_earthaccess_validation_passes_for_minimal_config():
    downloader = get_downloader(_cfg("earthaccess"))
    assert downloader.validate_config() == []


def test_harmony_validation_requires_template_for_scaffold_mode():
    downloader = get_downloader(_cfg("harmony"))
    errors = downloader.validate_config()
    assert any("swodlr_cmd_template" in item for item in errors)


def test_podaac_subscriber_only_is_allowed_when_commands_exist(monkeypatch):
    downloader = get_downloader(
        _cfg(
            "podaac",
            downloader_options={
                "use_subscriber": True,
                "use_downloader_cli": False,
                "subscriber_wait_timeout_s": 60,
            },
        )
    )
    monkeypatch.setattr(downloader, "_is_command_available", lambda _: True)
    errors = downloader.validate_config()
    assert all("scaffolded" not in item.lower() for item in errors)


def test_podaac_reports_missing_downloader_cli_binary(monkeypatch):
    downloader = get_downloader(
        _cfg(
            "podaac",
            downloader_options={
                "use_downloader_cli": True,
            },
        )
    )
    monkeypatch.setattr(downloader, "_is_command_available", lambda _: False)
    errors = downloader.validate_config()
    assert any("downloader cli not found" in item.lower() for item in errors)


def test_podaac_validates_positive_subscriber_timeouts(monkeypatch):
    downloader = get_downloader(
        _cfg(
            "podaac",
            downloader_options={
                "use_subscriber": True,
                "subscriber_wait_timeout_s": 0,
            },
        )
    )
    monkeypatch.setattr(downloader, "_is_command_available", lambda _: True)
    errors = downloader.validate_config()
    assert any("subscriber_wait_timeout_s" in item for item in errors)
