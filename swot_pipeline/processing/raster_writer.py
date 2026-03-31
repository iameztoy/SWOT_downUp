from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
import xarray as xr

from swot_pipeline.models import PipelineConfig
from swot_pipeline.products.base import ProductPlugin
from swot_pipeline.utils.time import to_rfc3339


def write_multiband_raster(
    output_path: Path,
    ds: xr.Dataset,
    arrays: dict[str, np.ndarray],
    plugin: ProductPlugin,
    config: PipelineConfig,
    acquisition_time,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    height, width = _infer_shape(arrays)
    crs, transform = _build_grid(ds, plugin, config, width=width, height=height)

    bands = list(arrays.keys())
    stack = np.stack([_coerce_band(arrays[name], height, width) for name in bands], axis=0)

    profile = {
        "width": width,
        "height": height,
        "count": stack.shape[0],
        "dtype": str(stack.dtype),
        "crs": crs,
        "transform": transform,
        "nodata": config.process.nodata,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "predictor": 2,
    }

    if config.process.write_cog:
        profile["driver"] = "COG"
    else:
        profile["driver"] = "GTiff"

    try:
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(stack)
            dst.descriptions = tuple(bands)
            dst.update_tags(
                product_short_name=plugin.short_name,
                acquisition_time=to_rfc3339(acquisition_time),
                output_mode=config.process.output_mode,
            )
    except rasterio.errors.RasterioIOError:
        # Fallback for environments where GDAL lacks COG driver support.
        profile["driver"] = "GTiff"
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(stack)
            dst.descriptions = tuple(bands)
            dst.update_tags(
                product_short_name=plugin.short_name,
                acquisition_time=to_rfc3339(acquisition_time),
                output_mode=config.process.output_mode,
                cog_requested=str(config.process.write_cog),
            )

    return output_path


def _coerce_band(arr: np.ndarray, height: int, width: int) -> np.ndarray:
    if arr.ndim > 2:
        arr = np.squeeze(arr)
    if arr.shape != (height, width):
        arr = np.reshape(arr, (height, width))
    return arr.astype(np.float32)


def _infer_shape(arrays: dict[str, np.ndarray]) -> tuple[int, int]:
    for arr in arrays.values():
        arr = np.squeeze(arr)
        if arr.ndim >= 2:
            return int(arr.shape[-2]), int(arr.shape[-1])
    raise ValueError("At least one 2D variable is required for raster output")


def _build_grid(ds: xr.Dataset, plugin: ProductPlugin, config: PipelineConfig, width: int, height: int):
    if config.process.output_mode == "native_utm":
        x_name = plugin.config.x_var
        y_name = plugin.config.y_var
        if x_name in ds and y_name in ds:
            x = ds[x_name].values
            y = ds[y_name].values
            transform = from_bounds(float(np.min(x)), float(np.min(y)), float(np.max(x)), float(np.max(y)), width, height)
            crs = f"EPSG:{plugin.config.native_epsg}" if plugin.config.native_epsg else ds.attrs.get("crs", "EPSG:4326")
            return crs, transform

    lat_name = plugin.config.latitude_var
    lon_name = plugin.config.longitude_var
    if lat_name in ds and lon_name in ds:
        lat = np.squeeze(ds[lat_name].values)
        lon = np.squeeze(ds[lon_name].values)
        if lat.ndim == 2:
            lat = lat[:, 0]
        if lon.ndim == 2:
            lon = lon[0, :]
        transform = from_bounds(
            float(np.nanmin(lon)),
            float(np.nanmin(lat)),
            float(np.nanmax(lon)),
            float(np.nanmax(lat)),
            width,
            height,
        )
        return "EPSG:4326", transform

    raise ValueError("Could not infer georeferencing grid from dataset")
