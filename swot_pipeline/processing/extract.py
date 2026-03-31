from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr
from shapely import contains_xy

from swot_pipeline.models import AOIConfig
from swot_pipeline.products.base import ProductPlugin
from swot_pipeline.utils.geometry import bbox_to_polygon, load_polygon


def extract_variables(
    ds: xr.Dataset,
    plugin: ProductPlugin,
    requested_bands: list[str],
    aoi: AOIConfig,
) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for band in requested_bands:
        source_var = plugin.map_variable(band)
        if source_var not in ds:
            raise KeyError(f"Variable '{source_var}' (mapped from '{band}') not found in dataset")
        arr = ds[source_var].squeeze(drop=True).values
        arrays[band] = np.asarray(arr)

    spatial_mask = build_spatial_mask(ds, plugin, aoi)
    if spatial_mask is not None:
        for key, arr in arrays.items():
            if np.issubdtype(arr.dtype, np.floating):
                arrays[key] = np.where(spatial_mask, arr, np.nan)
            else:
                arrays[key] = np.where(spatial_mask, arr, 0)

    return arrays


def build_spatial_mask(ds: xr.Dataset, plugin: ProductPlugin, aoi: AOIConfig) -> np.ndarray | None:
    if aoi.bbox is None and aoi.polygon_path is None and aoi.polygon_wkt is None:
        return None

    lat_name = plugin.config.latitude_var
    lon_name = plugin.config.longitude_var
    if lat_name not in ds or lon_name not in ds:
        # Without explicit lat/lon fields we skip AOI masking in this stage.
        return None

    lat = ds[lat_name].squeeze(drop=True).values
    lon = ds[lon_name].squeeze(drop=True).values

    if lat.ndim == 1 and lon.ndim == 1:
        lon2d, lat2d = np.meshgrid(lon, lat)
    elif lat.ndim == 2 and lon.ndim == 2:
        lon2d, lat2d = lon, lat
    else:
        return None

    polygon = load_polygon(aoi.polygon_path, aoi.polygon_wkt)
    if polygon is None and aoi.bbox:
        polygon = bbox_to_polygon(aoi.bbox)
    if polygon is None:
        return None

    # Buffer(0) fixes occasional invalid polygon rings from user-provided AOIs.
    polygon = polygon.buffer(0)
    return contains_xy(polygon, lon2d, lat2d)


def infer_2d_shape(arrays: dict[str, np.ndarray]) -> tuple[int, int]:
    for arr in arrays.values():
        if arr.ndim >= 2:
            return int(arr.shape[-2]), int(arr.shape[-1])
    raise ValueError("No 2D arrays available for raster writing")
