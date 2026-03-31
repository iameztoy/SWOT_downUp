from __future__ import annotations

import json
import math
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from shapely import from_wkt, to_geojson
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from swot_pipeline.aoi.presets import PRESET_REGIONS
from swot_pipeline.models import ChunkPlan


def parse_aoi_payload(payload: dict[str, Any]) -> BaseGeometry:
    method = (payload.get("method") or "bbox").lower()

    if method == "bbox":
        bbox = payload.get("bbox")
        if not bbox or len(bbox) != 4:
            raise ValueError("bbox method requires 4-value bbox [minx, miny, maxx, maxy]")
        return box(*[float(v) for v in bbox])

    if method == "wkt":
        text = payload.get("wkt") or ""
        if not text:
            raise ValueError("wkt method requires a non-empty WKT string")
        return from_wkt(text)

    if method in {"geojson", "map_polygon", "map_rectangle"}:
        geojson_obj = payload.get("geojson")
        if isinstance(geojson_obj, str):
            geojson_obj = json.loads(geojson_obj)
        if not geojson_obj:
            raise ValueError("geojson method requires geojson payload")
        if geojson_obj.get("type") == "Feature":
            return shape(geojson_obj["geometry"])
        if geojson_obj.get("type") == "FeatureCollection":
            features = geojson_obj.get("features", [])
            if not features:
                raise ValueError("FeatureCollection has no features")
            return unary_union([shape(f["geometry"]) for f in features])
        return shape(geojson_obj)

    if method == "preset":
        preset_id = payload.get("preset_id")
        if not preset_id:
            raise ValueError("preset method requires preset_id")
        preset = PRESET_REGIONS.get(preset_id)
        if not preset:
            raise ValueError(f"Unknown preset_id={preset_id}")
        return box(*preset["bbox"])

    if method == "shapefile_zip":
        zip_path = payload.get("zip_path")
        if not zip_path:
            raise ValueError("shapefile_zip method requires zip_path")
        return _parse_shapefile_zip(Path(zip_path))

    raise ValueError(f"Unsupported AOI method '{method}'")


def geometry_summary(geom: BaseGeometry) -> dict[str, Any]:
    minx, miny, maxx, maxy = geom.bounds
    area_km2 = approximate_area_km2(geom)
    return {
        "geometry_geojson": json.loads(to_geojson(geom)),
        "bbox": [minx, miny, maxx, maxy],
        "area_km2": area_km2,
        "size_class": classify_aoi_size(area_km2),
        "crs": "EPSG:4326",
        "is_valid": bool(geom.is_valid),
        "warnings": _warnings_for_extent(geom, area_km2),
    }


def classify_aoi_size(area_km2: float) -> str:
    if area_km2 < 50_000:
        return "small"
    if area_km2 < 500_000:
        return "medium"
    return "large"


def chunk_geometry(
    geom: BaseGeometry,
    max_tile_area_km2: float,
    max_tile_span_deg: float,
    max_tiles: int,
) -> list[ChunkPlan]:
    minx, miny, maxx, maxy = geom.bounds
    width = maxx - minx
    height = maxy - miny

    nx = max(1, math.ceil(width / max_tile_span_deg))
    ny = max(1, math.ceil(height / max_tile_span_deg))

    total_area = approximate_area_km2(geom)
    if total_area > max_tile_area_km2:
        area_factor = math.sqrt(total_area / max_tile_area_km2)
        nx = max(nx, math.ceil(nx * area_factor))
        ny = max(ny, math.ceil(ny * area_factor))

    nx = min(nx, max_tiles)
    ny = min(ny, max_tiles)

    dx = width / nx if nx else width
    dy = height / ny if ny else height

    chunks: list[ChunkPlan] = []
    index = 0
    for ix in range(nx):
        for iy in range(ny):
            tx0 = minx + ix * dx
            tx1 = minx + (ix + 1) * dx
            ty0 = miny + iy * dy
            ty1 = miny + (iy + 1) * dy
            tile = box(tx0, ty0, tx1, ty1).intersection(geom)
            if tile.is_empty:
                continue
            area = approximate_area_km2(tile)
            label = f"tile_{ix:03d}_{iy:03d}"
            chunks.append(ChunkPlan(index=index, bbox=tuple(tile.bounds), area_km2=area, label=label))
            index += 1
            if len(chunks) >= max_tiles:
                return chunks

    return chunks


def preset_regions() -> list[dict[str, Any]]:
    items = []
    for preset_id, data in PRESET_REGIONS.items():
        items.append({"id": preset_id, **data})
    return sorted(items, key=lambda x: x["label"])


def approximate_area_km2(geom: BaseGeometry) -> float:
    try:
        from pyproj import Geod

        geod = Geod(ellps="WGS84")
        area, _ = geod.geometry_area_perimeter(geom)
        return abs(area) / 1_000_000.0
    except Exception:
        minx, miny, maxx, maxy = geom.bounds
        avg_lat_rad = math.radians((miny + maxy) / 2.0)
        km_per_deg_lat = 111.32
        km_per_deg_lon = 111.32 * math.cos(avg_lat_rad)
        width_km = abs(maxx - minx) * km_per_deg_lon
        height_km = abs(maxy - miny) * km_per_deg_lat
        return width_km * height_km


def _warnings_for_extent(geom: BaseGeometry, area_km2: float) -> list[str]:
    warnings: list[str] = []
    if not geom.is_valid:
        warnings.append("AOI geometry is invalid and may produce unstable results")
    if area_km2 > 500_000:
        warnings.append("Large AOI detected. Chunking will be recommended.")
    if area_km2 > 2_000_000:
        warnings.append("Extremely large AOI. Expect many chunks and long runtimes.")
    return warnings


def _parse_shapefile_zip(path: Path) -> BaseGeometry:
    if not path.exists():
        raise ValueError(f"Zip file not found: {path}")

    try:
        import shapefile  # pyshp
    except ImportError as exc:
        raise RuntimeError("Shapefile zip support requires 'pyshp' package") from exc

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(tmp_path)

        shp_files = list(tmp_path.rglob("*.shp"))
        if not shp_files:
            raise ValueError("No .shp file found inside zip")

        reader = shapefile.Reader(str(shp_files[0]))
        geoms = [shape(s.__geo_interface__) for s in reader.shapes()]
        if not geoms:
            raise ValueError("Shapefile contains no geometries")
        return unary_union(geoms)
