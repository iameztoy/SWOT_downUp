from swot_pipeline.utils.time import parse_datetime_from_filename


def test_parse_iso_style_timestamp():
    name = "SWOT_L2_HR_Raster_100m_D_20240601T123045_foo.nc"
    dt = parse_datetime_from_filename(name)
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 6
    assert dt.day == 1


def test_parse_compact_timestamp():
    name = "SWOT_20240601123045_bar.nc"
    dt = parse_datetime_from_filename(name)
    assert dt is not None
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 45


def test_parse_timestamp_missing_returns_none():
    assert parse_datetime_from_filename("SWOT_no_time.nc") is None
