from __future__ import annotations

PRESET_REGIONS: dict[str, dict[str, object]] = {
    "world": {
        "label": "World",
        "bbox": (-180.0, -85.0, 180.0, 85.0),
        "kind": "world",
    },
    "continent_africa": {
        "label": "Africa",
        "bbox": (-20.0, -35.0, 55.0, 38.0),
        "kind": "continent",
    },
    "continent_europe": {
        "label": "Europe",
        "bbox": (-31.0, 34.0, 45.0, 72.0),
        "kind": "continent",
    },
    "continent_north_america": {
        "label": "North America",
        "bbox": (-170.0, 5.0, -50.0, 83.0),
        "kind": "continent",
    },
    "continent_south_america": {
        "label": "South America",
        "bbox": (-82.0, -56.0, -34.0, 13.0),
        "kind": "continent",
    },
    "continent_asia": {
        "label": "Asia",
        "bbox": (25.0, -11.0, 180.0, 81.0),
        "kind": "continent",
    },
    "continent_oceania": {
        "label": "Oceania",
        "bbox": (110.0, -50.0, 180.0, 0.0),
        "kind": "continent",
    },
    "country_spain": {
        "label": "Spain",
        "bbox": (-9.5, 35.8, 3.5, 43.9),
        "kind": "country",
    },
    "country_usa": {
        "label": "United States (CONUS + AK + HI approx)",
        "bbox": (-171.0, 18.0, -66.0, 72.0),
        "kind": "country",
    },
    "basin_placeholder_001": {
        "label": "Basin Placeholder 001",
        "bbox": (-5.0, 35.0, 5.0, 45.0),
        "kind": "basin_placeholder",
    },
}
