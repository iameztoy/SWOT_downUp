from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely import wkt


def load_polygon(polygon_path: Path | None = None, polygon_wkt: str | None = None) -> BaseGeometry | None:
    if polygon_wkt:
        return wkt.loads(polygon_wkt)
    if polygon_path is None:
        return None

    data = json.loads(Path(polygon_path).read_text())
    if "type" in data and data["type"] == "FeatureCollection":
        if not data.get("features"):
            raise ValueError("FeatureCollection has no features")
        return shape(data["features"][0]["geometry"])
    if "type" in data and data["type"] == "Feature":
        return shape(data["geometry"])
    return shape(data)


def bbox_to_polygon(bbox: tuple[float, float, float, float]) -> BaseGeometry:
    minx, miny, maxx, maxy = bbox
    return shape(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [minx, miny],
                    [maxx, miny],
                    [maxx, maxy],
                    [minx, maxy],
                    [minx, miny],
                ]
            ],
        }
    )
